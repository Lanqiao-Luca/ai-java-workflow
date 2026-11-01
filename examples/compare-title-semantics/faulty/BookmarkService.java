import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Synthetic in-memory service. Caller identity must come from a trusted boundary. */
public final class BookmarkService {
    public record Bookmark(String owner, String title, List<String> tags,
                           long savedSequence, long version) {
        public Bookmark { tags = List.copyOf(tags); }
    }
    private final Map<String, Bookmark> entries = new HashMap<>();
    private final List<String> events = new ArrayList<>();

    public BookmarkService() {
        entries.put("demo", new Bookmark("owner-demo", "Old title", List.of("reading"), 7, 0));
    }
    public synchronized Bookmark get(String reference) {
        Bookmark current = entries.get(reference);
        if (current == null) throw new IllegalArgumentException("not found");
        return current;
    }
    public synchronized int auditCount() { return events.size(); }

    public synchronized Bookmark rename(String reference, String caller,
                                         long expectedVersion, String title) {
        Bookmark current = get(reference);
        if (!current.owner().equals(caller)) throw new SecurityException("not owner");
        if (current.version() != expectedVersion) throw new IllegalStateException("stale version");
        if (title == null) throw new IllegalArgumentException("missing title");
        String normalized = title.replace(" ", "");
        if (normalized.isEmpty()) throw new IllegalArgumentException("blank title");
        if (current.title().equals(normalized)) return current;
        Bookmark updated = new Bookmark(current.owner(), normalized, current.tags(),
                                        current.savedSequence(), current.version() + 1);
        entries.put(reference, updated);
        events.add("title changed");
        return updated;
    }
}
