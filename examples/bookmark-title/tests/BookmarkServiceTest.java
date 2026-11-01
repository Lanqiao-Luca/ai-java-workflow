/** Framework-free contract tests. Checks do not depend on JVM assertion flags. */
public final class BookmarkServiceTest {
    private static int passed;
    private static int failed;
    private static void check(boolean value) {
        if (!value) throw new AssertionError("contract mismatch");
    }
    private static void test(String id, Runnable action) {
        try { action.run(); passed++; System.out.println("PASS " + id); }
        catch (RuntimeException | AssertionError e) {
            failed++; System.out.println("FAIL " + id + " " + e.getClass().getSimpleName());
        }
    }
    private static void rejects(BookmarkService s, Class<? extends RuntimeException> kind,
                                Runnable action) {
        var before = s.get("demo");
        int count = s.auditCount();
        boolean rejected = false;
        try { action.run(); }
        catch (RuntimeException e) {
            if (!kind.isInstance(e)) throw e;
            rejected = true;
        }
        check(rejected);
        check(s.get("demo").equals(before));
        check(s.auditCount() == count);
    }
    public static void main(String[] args) {
        test("trim", () -> {
            var s = new BookmarkService();
            var result = s.rename("demo", "owner-demo", 0, "  New title  ");
            check(result.title().equals("New title"));
            check(s.get("demo").equals(result));
        });
        test("blank", () -> {
            var s = new BookmarkService();
            rejects(s, IllegalArgumentException.class, () -> s.rename("demo", "owner-demo", 0, "   "));
        });
        test("empty", () -> {
            var s = new BookmarkService();
            rejects(s, IllegalArgumentException.class, () -> s.rename("demo", "owner-demo", 0, ""));
        });
        test("null", () -> {
            var s = new BookmarkService();
            rejects(s, IllegalArgumentException.class, () -> s.rename("demo", "owner-demo", 0, null));
        });
        test("owner", () -> {
            var s = new BookmarkService();
            rejects(s, SecurityException.class, () -> s.rename("demo", "other-demo", 0, "New"));
        });
        test("owner-before-title", () -> {
            var s = new BookmarkService();
            rejects(s, SecurityException.class, () -> s.rename("demo", "other-demo", 0, null));
        });
        test("stale", () -> {
            var s = new BookmarkService();
            rejects(s, IllegalStateException.class, () -> s.rename("demo", "owner-demo", 1, "New"));
        });
        test("preserved-fields-and-audit", () -> {
            var s = new BookmarkService();
            var previous = s.get("demo");
            var result = s.rename("demo", "owner-demo", 0, "New");
            check(result.owner().equals(previous.owner()));
            check(result.tags().equals(previous.tags()));
            check(result.savedSequence() == previous.savedSequence());
            check(result.version() == previous.version() + 1);
            check(s.auditCount() == 1);
            check(s.get("demo").equals(result));
        });
        test("normalized-noop", () -> {
            var s = new BookmarkService();
            var previous = s.get("demo");
            check(s.rename("demo", "owner-demo", 0, "  Old title  ").equals(previous));
            check(s.auditCount() == 0);
        });
        test("plain-noop", () -> {
            var s = new BookmarkService();
            var previous = s.get("demo");
            check(s.rename("demo", "owner-demo", 0, "Old title").equals(previous));
            check(s.auditCount() == 0);
        });
        test("missing", () -> {
            var s = new BookmarkService();
            rejects(s, IllegalArgumentException.class, () -> s.rename("missing", "owner-demo", 0, "New"));
        });
        test("stale-after-success", () -> {
            var s = new BookmarkService();
            s.rename("demo", "owner-demo", 0, "New");
            rejects(s, IllegalStateException.class, () -> s.rename("demo", "owner-demo", 0, "Again"));
        });
        System.out.println("SUMMARY passed=" + passed + " failed=" + failed);
        if (failed != 0) throw new AssertionError("contract tests failed");
    }
}
