package example.workflow;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class TagService {
    public record Bookmark(String owner, String title, List<String> tags, long savedSequence, long version) {
        public Bookmark { tags = List.copyOf(tags); }
    }
    public static final class Rejected extends RuntimeException {
        private final int status;
        private final String code;
        public Rejected(int status, String code) { super(code); this.status = status; this.code = code; }
        public int status() { return status; }
        public String code() { return code; }
    }
    private final Map<String, Bookmark> entries = new HashMap<>();
    private final List<String> audit = new ArrayList<>();

    public TagService() { reset(); }
    public synchronized void reset() {
        entries.clear(); audit.clear();
        entries.put("demo", new Bookmark("reader-demo", "Read later", List.of("old"), 11, 0));
    }
    public synchronized Bookmark get(String id) {
        Bookmark item = entries.get(id);
        if (item == null) throw new Rejected(404, "NOT_FOUND");
        return item;
    }
    public synchronized int auditCount() { return audit.size(); }

    public synchronized Bookmark replace(String id, String actor, Long expectedVersion, List<String> tags) {
        Bookmark current = get(id);
        if (!current.owner().equals(actor)) throw new Rejected(403, "NOT_OWNER");
        if (expectedVersion == null) throw new Rejected(400, "MISSING_VERSION");
        if (current.version() != expectedVersion.longValue()) throw new Rejected(409, "STALE_VERSION");
        List<String> normalized = normalize(tags);
        if (current.tags().equals(normalized)) return current;
        Bookmark changed = new Bookmark(current.owner(), current.title(), normalized,
                                         current.savedSequence(), current.version() + 1);
        entries.put(id, changed);
        audit.add("TAGS_REPLACED");
        return changed;
    }

    private List<String> normalize(List<String> tags) {
        if (tags == null) throw new Rejected(400, "MISSING_TAGS");
        LinkedHashSet<String> unique = new LinkedHashSet<>();
        for (String tag : tags) {
            if (tag == null || tag.trim().isEmpty()) throw new Rejected(400, "INVALID_TAG");
            unique.add(tag.trim());
        }
        return List.copyOf(unique);
    }
}
