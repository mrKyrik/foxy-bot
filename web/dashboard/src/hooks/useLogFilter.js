import { useMemo } from 'react';
import { parseTimestamp } from '../utils/time';

export const useLogFilter = (logs, { 
    typeFilter, 
    eventMatcher, 
    selectedEvents, 
    selectedTags, 
    reducer 
}) => {
    return useMemo(() => {
        let earliest = Number.MAX_SAFE_INTEGER;
        let latest = 0;

        const sortedLogs = [...logs].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        const filteredLogs = [];

        sortedLogs.forEach(log => {
            const type = log.event_type;

            // 1. Type filter
            if (typeFilter && !typeFilter(log, type)) return;

            // 2. Event Matcher
            if (selectedEvents && selectedEvents.length > 0 && eventMatcher) {
                if (!eventMatcher(log, type, selectedEvents)) return;
            }

            // 3. Tags check
            if (selectedTags && selectedTags.length > 0) {
                const isMatch = selectedTags.some(tag => {
                    if (tag.type === 'user') return tag.id === log.user_id || tag.id === log.admin_id || tag.id === log.inviter_id;
                    if (tag.type === 'channel') return tag.id === log.channel_id;
                    if (tag.type === 'role') return tag.id === log.role_id || tag.id === log.channel_id || (log.details && log.details.includes(tag.name));
                    if (tag.type === 'category') return tag.id === log.category_id;
                    return false;
                });
                if (!isMatch) return;
            }

            const ts = parseTimestamp(log.timestamp);
            log.ts = ts;
            if (ts < earliest) earliest = ts;
            if (ts > latest) latest = ts;

            filteredLogs.push(log);
        });

        // 4. Reduce to categories or nested objects
        const parsed = reducer ? reducer(filteredLogs) : filteredLogs;

        return { parsed, earliest, latest, filteredLogs };
    }, [logs, selectedEvents, selectedTags, typeFilter, eventMatcher, reducer]);
};
