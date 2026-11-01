SELECT id FROM bookmarks WHERE owner_id = :owner AND saved_seq < :seq ORDER BY saved_seq DESC, id DESC LIMIT :size;
