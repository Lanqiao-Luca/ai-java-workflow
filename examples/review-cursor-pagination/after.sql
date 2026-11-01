SELECT id FROM bookmarks WHERE owner_id = :owner AND (saved_seq < :seq OR (saved_seq = :seq AND id < :id)) ORDER BY saved_seq DESC, id DESC LIMIT :size;
