/**
 * Wix Velo webhook handler for Meridian Signal Service
 * Receives and processes signal and report webhooks with full middleware stack
 */

import { query as wixQuery, insert as wixInsert, update as wixUpdate } from 'wix-data';
import { sendEmail as wixSendEmail } from 'wix-mail';
import { getCurrentMemberId, getMemberById } from 'wix-members.currentMember';

const SHARED_SECRET = process.env.WIX_MERIDIAN_HMAC_SECRET;
const MERIDIAN_CONFIG = {
    geographies: {
        'Atlanta-GA': { wixRegion: 'Atlanta', state: 'GA' },
        '30301': { wixZip: '30301', state: 'GA' },
    },
    signalThresholds: {
        'price_drop_30d': { percentChange: -5 },
        'low_inventory': { monthsOfInventory: 3 },
    },
    notificationTemplates: {
        'signal_fired': 'signal-alert-email',
        'report_ready': 'report-ready-email',
    },
};

const COLLECTIONS = {
    signalLogs: 'SignalLogs',
    webhookAudit: 'WebhookAudit',
    memberListingMap: 'MemberListingMap',
    notificationPreferences: 'NotificationPreferences',
    analyticsEvents: 'AnalyticsEvents',
    failedWebhooks: 'FailedWebhooks',
};

// ============================================================================
// Main Webhook Handlers
// ============================================================================

export async function post_signalFired(request) {
    try {
        // 1. Security validation
        const sig = request.headers['x-meridian-signature'];
        const body = await request.body.text();
        if (!verifyHmac(sig, body, SHARED_SECRET)) {
            await auditWebhook('signalFired', 'REJECTED', 'Invalid HMAC signature', body);
            return new Response('Unauthorized', { status: 401 });
        }

        // 2. Parse and validate payload
        const payload = JSON.parse(body);
        const validationResult = validateSignalPayload(payload);
        if (!validationResult.valid) {
            await auditWebhook('signalFired', 'INVALID', validationResult.error, body);
            return new Response('Invalid payload', { status: 400 });
        }

        // 3. De-duplication check
        if (await isDuplicateWebhook(payload.id, 'signal')) {
            await auditWebhook('signalFired', 'DUPLICATE', 'Idempotency key exists', body);
            return new Response('OK', { status: 200 });
        }

        // 4. Transform and enrich data
        const enrichedPayload = await transformSignalPayload(payload);

        // 5. Persist to CMS
        await persistSignalLog(enrichedPayload);

        // 6. Trigger notifications
        await triggerSignalNotifications(enrichedPayload);

        // 7. Track analytics
        await trackAnalyticsEvent('signal_fired', enrichedPayload);

        // 8. Log successful processing
        await auditWebhook('signalFired', 'SUCCESS', 'Signal processed', body);

        return new Response('OK', { status: 200 });
    } catch (error) {
        await handleWebhookError('signalFired', error, request);
        return new Response('Error processing webhook', { status: 500 });
    }
}

export async function post_reportGenerated(request) {
    try {
        const sig = request.headers['x-meridian-signature'];
        const body = await request.body.text();

        if (!verifyHmac(sig, body, SHARED_SECRET)) {
            await auditWebhook('reportGenerated', 'REJECTED', 'Invalid HMAC signature', body);
            return new Response('Unauthorized', { status: 401 });
        }

        const payload = JSON.parse(body);
        const validationResult = validateReportPayload(payload);
        if (!validationResult.valid) {
            await auditWebhook('reportGenerated', 'INVALID', validationResult.error, body);
            return new Response('Invalid payload', { status: 400 });
        }

        if (await isDuplicateWebhook(payload.id, 'report')) {
            await auditWebhook('reportGenerated', 'DUPLICATE', 'Idempotency key exists', body);
            return new Response('OK', { status: 200 });
        }

        const enrichedPayload = await transformReportPayload(payload);
        await persistReportCompletion(enrichedPayload);
        await triggerReportNotifications(enrichedPayload);
        await trackAnalyticsEvent('report_generated', enrichedPayload);
        await auditWebhook('reportGenerated', 'SUCCESS', 'Report processed', body);

        return new Response('OK', { status: 200 });
    } catch (error) {
        await handleWebhookError('reportGenerated', error, request);
        return new Response('Error processing webhook', { status: 500 });
    }
}

// ============================================================================
// Layer 1: Security & Validation
// ============================================================================

function verifyHmac(signature, body, secret) {
    const crypto = require('crypto');
    const expected = crypto.createHmac('sha256', secret).update(body, 'utf8').digest('hex');
    return signature === `sha256=${expected}`;
}

function validateSignalPayload(payload) {
    const required = ['id', 'signal_type', 'geography', 'geo_type', 'triggered_at', 'listing_ids'];
    for (const field of required) {
        if (!payload[field]) return { valid: false, error: `Missing field: ${field}` };
    }
    if (!Array.isArray(payload.listing_ids)) return { valid: false, error: 'listing_ids must be array' };
    return { valid: true };
}

function validateReportPayload(payload) {
    const required = ['id', 'report_type', 'geography', 'geo_type', 'report_date', 'metrics'];
    for (const field of required) {
        if (!payload[field]) return { valid: false, error: `Missing field: ${field}` };
    }
    return { valid: true };
}

async function isDuplicateWebhook(webhookId, type) {
    try {
        const existing = await wixQuery(COLLECTIONS.webhookAudit)
            .eq('webhookId', webhookId)
            .eq('type', type)
            .find();
        return existing.items.length > 0;
    } catch (e) {
        console.error('Duplicate check error:', e);
        return false;
    }
}

// ============================================================================
// Layer 2: Data Transformation & Enrichment
// ============================================================================

async function transformSignalPayload(payload) {
    // Map geography to Wix region
    const geoConfig = MERIDIAN_CONFIG.geographies[payload.geography] || {};
    
    // Resolve member listings
    const memberListings = await resolveMemberListings(payload.listing_ids);
    
    // Check member notification preferences
    const preferences = await getNotificationPreferences(memberListings[0]?.memberId);

    return {
        ...payload,
        wixRegion: geoConfig.wixRegion,
        wixZip: geoConfig.wixZip,
        memberListings,
        notificationEnabled: preferences?.emailNotifications ?? true,
        processedAt: new Date().toISOString(),
    };
}

async function transformReportPayload(payload) {
    const geoConfig = MERIDIAN_CONFIG.geographies[payload.geography] || {};
    const memberListings = await resolveMemberListings(payload.listing_ids || []);

    return {
        ...payload,
        wixRegion: geoConfig.wixRegion,
        wixZip: geoConfig.wixZip,
        memberListings,
        processedAt: new Date().toISOString(),
    };
}

async function resolveMemberListings(listingIds) {
    try {
        const results = await wixQuery(COLLECTIONS.memberListingMap)
            .hasSome('meridianListingIds', listingIds)
            .find();
        return results.items;
    } catch (e) {
        console.error('Member listing lookup error:', e);
        return [];
    }
}

async function getNotificationPreferences(memberId) {
    if (!memberId) return null;
    try {
        const result = await wixQuery(COLLECTIONS.notificationPreferences)
            .eq('memberId', memberId)
            .find();
        return result.items[0];
    } catch (e) {
        console.error('Preference lookup error:', e);
        return null;
    }
}

// ============================================================================
// Layer 3: Persistence Layer
// ============================================================================

async function persistSignalLog(enrichedPayload) {
    const signalLog = {
        meridianId: enrichedPayload.id,
        signalType: enrichedPayload.signal_type,
        geography: enrichedPayload.geography,
        geoType: enrichedPayload.geo_type,
        wixRegion: enrichedPayload.wixRegion,
        wixZip: enrichedPayload.wixZip,
        triggeredAt: enrichedPayload.triggered_at,
        listingIds: enrichedPayload.listing_ids,
        memberListings: enrichedPayload.memberListings,
        rawPayload: enrichedPayload,
        status: 'received',
        createdAt: new Date().toISOString(),
    };

    try {
        const result = await wixInsert(COLLECTIONS.signalLogs, signalLog);
        console.log('Signal log persisted:', result._id);
        return result;
    } catch (e) {
        console.error('Failed to persist signal log:', e);
        throw e;
    }
}

async function persistReportCompletion(enrichedPayload) {
    const report = {
        meridianId: enrichedPayload.id,
        reportType: enrichedPayload.report_type,
        geography: enrichedPayload.geography,
        geoType: enrichedPayload.geo_type,
        reportDate: enrichedPayload.report_date,
        metrics: enrichedPayload.metrics,
        wixRegion: enrichedPayload.wixRegion,
        memberListings: enrichedPayload.memberListings,
        rawPayload: enrichedPayload,
        status: 'completed',
        deliveredAt: new Date().toISOString(),
        createdAt: new Date().toISOString(),
    };

    try {
        const result = await wixInsert(COLLECTIONS.signalLogs, report);
        console.log('Report persisted:', result._id);
        return result;
    } catch (e) {
        console.error('Failed to persist report:', e);
        throw e;
    }
}

// ============================================================================
// Layer 4: Notification Engine
// ============================================================================

async function triggerSignalNotifications(enrichedPayload) {
    if (!enrichedPayload.notificationEnabled) {
        console.log('Notifications disabled for signal');
        return;
    }

    const recipients = enrichedPayload.memberListings.map(m => m.memberEmail).filter(Boolean);
    if (recipients.length === 0) return;

    const emailContent = buildSignalEmailContent(enrichedPayload);
    await sendEmailNotification(recipients, emailContent);
}

async function triggerReportNotifications(enrichedPayload) {
    const recipients = enrichedPayload.memberListings.map(m => m.memberEmail).filter(Boolean);
    if (recipients.length === 0) return;

    const emailContent = buildReportEmailContent(enrichedPayload);
    await sendEmailNotification(recipients, emailContent);
}

function buildSignalEmailContent(payload) {
    return {
        subject: `🔔 Signal Alert: ${payload.signal_type} in ${payload.geography}`,
        html: `
            <h2>Signal Alert</h2>
            <p><strong>Type:</strong> ${payload.signal_type}</p>
            <p><strong>Geography:</strong> ${payload.geography} (${payload.geo_type})</p>
            <p><strong>Triggered:</strong> ${new Date(payload.triggered_at).toLocaleString()}</p>
            <p><strong>Affected Listings:</strong> ${payload.listing_ids.length}</p>
            <a href="https://yoursite.com/signals?id=${payload.id}">View Details</a>
        `,
    };
}

function buildReportEmailContent(payload) {
    return {
        subject: `📊 Market Report Ready: ${payload.geography}`,
        html: `
            <h2>Market Report Available</h2>
            <p><strong>Geography:</strong> ${payload.geography} (${payload.geo_type})</p>
            <p><strong>Report Date:</strong> ${payload.report_date}</p>
            <p><strong>Metrics Included:</strong> ${Object.keys(payload.metrics).join(', ')}</p>
            <a href="https://yoursite.com/reports?id=${payload.id}">Download Report</a>
        `,
    };
}

async function sendEmailNotification(recipients, emailContent) {
    try {
        await wixSendEmail({
            to: recipients,
            subject: emailContent.subject,
            html: emailContent.html,
        });
        console.log('Email sent to:', recipients);
    } catch (e) {
        console.error('Failed to send email:', e);
        throw e;
    }
}

// ============================================================================
// Layer 5: Error Handling & Audit Trail
// ============================================================================

async function auditWebhook(type, status, reason, rawBody) {
    const auditRecord = {
        type,
        status,
        reason,
        rawBody,
        timestamp: new Date().toISOString(),
        webhookId: extractWebhookId(rawBody),
    };

    try {
        await wixInsert(COLLECTIONS.webhookAudit, auditRecord);
    } catch (e) {
        console.error('Audit logging error:', e);
    }
}

async function handleWebhookError(handlerName, error, request) {
    const failedRecord = {
        handler: handlerName,
        error: error.message,
        stack: error.stack,
        requestHeaders: Object.fromEntries(request.headers),
        timestamp: new Date().toISOString(),
        retryCount: 0,
        status: 'pending',
    };

    try {
        const result = await wixInsert(COLLECTIONS.failedWebhooks, failedRecord);
        console.log('Failed webhook queued for retry:', result._id);
    } catch (e) {
        console.error('Failed to queue webhook for retry:', e);
    }

    console.error(`Webhook error in ${handlerName}:`, error);
}

function extractWebhookId(rawBody) {
    try {
        const obj = JSON.parse(rawBody);
        return obj.id;
    } catch {
        return null;
    }
}

// ============================================================================
// Layer 6: Analytics & Tracking
// ============================================================================

async function trackAnalyticsEvent(eventType, payload) {
    const analyticsEvent = {
        eventType,
        geography: payload.geography,
        geoType: payload.geo_type,
        memberCount: (payload.memberListings || []).length,
        listingCount: (payload.listing_ids || []).length,
        meridianId: payload.id,
        timestamp: new Date().toISOString(),
    };

    try {
        await wixInsert(COLLECTIONS.analyticsEvents, analyticsEvent);
    } catch (e) {
        console.error('Analytics tracking error:', e);
    }
}

// ============================================================================
// Layer 7: Configuration Management
// ============================================================================

function getSignalThreshold(signalType) {
    return MERIDIAN_CONFIG.signalThresholds[signalType];
}

function getNotificationTemplate(templateKey) {
    return MERIDIAN_CONFIG.notificationTemplates[templateKey];
}