"""Assess explicitly supplied page observations; no fetch, authorization or business verdict."""


class CoverageError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise CoverageError(message)


def assess(scope, pages):
    need(isinstance(scope, dict) and set(scope) == {'source_id', 'snapshot', 'needle', 'mode', 'max_pages', 'probe_id'}, 'scope fields')
    for field in ('source_id', 'snapshot', 'needle', 'probe_id'):
        need(isinstance(scope[field], str) and bool(scope[field].strip()), 'scope identity')
    need(isinstance(scope['mode'], str) and scope['mode'] in {'sample', 'complete'} and type(scope['max_pages']) is int
         and 0 < scope['max_pages'] <= 100, 'mode or budget')
    need(isinstance(pages, list) and len(pages) <= scope['max_pages'], 'page budget')
    result = {'status': 'NOT_RUN', 'pages_observed': 0, 'rows_observed': 0, 'match_ids': [],
              'probe_observed': False, 'coverage_complete': False, 'absence': 'unknown', 'next_cursor': None}
    cursor, seen_cursors, seen_rows = None, set(), set()
    for index, page in enumerate(pages):
        need(isinstance(page, dict) and set(page) == {'source_id', 'snapshot', 'needle', 'cursor_in',
             'cursor_out', 'status', 'rows', 'finished', 'truncated'}, 'page fields')
        need(all(page[key] == scope[key] for key in ('source_id', 'snapshot', 'needle')), 'mixed query context')
        need(page['cursor_in'] == cursor, 'broken cursor chain')
        need(type(page['finished']) is bool and type(page['truncated']) is bool, 'quality flags')
        need(isinstance(page['status'], str) and page['status'] in {'OK', 'DENIED', 'ERROR', 'UNKNOWN'} and isinstance(page['rows'], list), 'page result')
        result['pages_observed'] += 1
        if page['status'] != 'OK':
            need(not page['rows'] and not page['finished'] and page['cursor_out'] is None, 'failed query is not zero')
            need(index == len(pages) - 1, 'new pages after failed or unknown action')
            result['status'] = page['status']
            return result
        for row in page['rows']:
            need(isinstance(row, dict) and set(row) == {'id', 'text'}
                 and all(isinstance(row[k], str) and bool(row[k]) for k in ('id', 'text')), 'row fields')
            need(row['id'] not in seen_rows, 'duplicate row identity')
            seen_rows.add(row['id'])
            result['rows_observed'] += 1
            if row['id'] == scope['probe_id']:
                result['probe_observed'] = True
            elif scope['needle'] in row['text']:
                result['match_ids'].append(row['id'])
        if page['finished']:
            need(page['cursor_out'] is None, 'finished cursor')
        else:
            need(isinstance(page['cursor_out'], str) and page['cursor_out']
                 and page['cursor_out'] not in seen_cursors, 'cursor loop or missing checkpoint')
            seen_cursors.add(page['cursor_out'])
        result['next_cursor'] = page['cursor_out']
        terminal = page['truncated'] or page['finished'] or (scope['mode'] == 'sample' and result['match_ids'])
        if terminal:
            need(index == len(pages) - 1, 'overcollection beyond stopping condition')
            if page['truncated']:
                result['status'] = 'PARTIAL'
            elif scope['mode'] == 'sample':
                result['status'] = 'SAMPLE_FOUND' if result['match_ids'] else 'SAMPLE_NOT_FOUND'
            elif result['match_ids']:
                result.update(status='COMPLETE_MATCH', coverage_complete=True)
            elif result['probe_observed']:
                result.update(status='COMPLETE_EMPTY', coverage_complete=True, absence='bounded_empty')
            else:
                result['status'] = 'UNRESOLVED_EMPTY'
            return result
        cursor = page['cursor_out']
        result['status'] = 'PARTIAL'
    return result
