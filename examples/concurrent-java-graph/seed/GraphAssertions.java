import java.util.Arrays;
import java.util.List;

public class GraphAssertions {
    private static int checks;
    private static void check(boolean ok) {
        if (!ok) throw new AssertionError("synthetic contract mismatch");
        checks++;
    }
    private static void rejects(Runnable operation) {
        boolean rejected = false;
        try { operation.run(); } catch (IllegalArgumentException e) { rejected = true; }
        check(rejected);
    }
    public static void main(String[] args) {
        check(TitlePolicy.normalize(" read ").equals("read"));
        rejects(() -> TitlePolicy.normalize(" "));
        rejects(() -> TitlePolicy.normalize(null));
        check(TagPolicy.normalize(List.of(" a ", "a", "B")).equals(List.of("a", "B")));
        check(TagPolicy.normalize(List.of()).isEmpty());
        rejects(() -> TagPolicy.normalize(null));
        rejects(() -> TagPolicy.normalize(List.of("a", " ")));
        rejects(() -> TagPolicy.normalize(Arrays.asList("a", null)));
        if (checks != 8) throw new AssertionError("check count drift");
        System.out.println("JAVA_GRAPH_OK checks=8");
    }
}
