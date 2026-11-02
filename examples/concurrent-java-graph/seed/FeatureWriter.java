import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import javax.tools.ToolProvider;

/** Independent synthetic feature Workflow. Compiler API stays in this JVM, no child process. */
class FeatureWriter {
    public static void main(String[] args) throws Exception {
        String mode = args[0];
        String name;
        String source;
        if (mode.equals("title")) {
            name = "TitlePolicy";
            source = """
                public class TitlePolicy {
                    public static String normalize(String title) {
                        if (title == null || title.trim().isEmpty()) throw new IllegalArgumentException();
                        return title.trim();
                    }
                }
                """;
        } else if (mode.equals("tags")) {
            name = "TagPolicy";
            source = """
                import java.util.List;
                import java.util.LinkedHashSet;
                public class TagPolicy {
                    public static List<String> normalize(List<String> tags) {
                        if (tags == null) throw new IllegalArgumentException();
                        var result = new LinkedHashSet<String>();
                        for (String tag : tags) {
                            if (tag == null || tag.trim().isEmpty()) throw new IllegalArgumentException();
                            result.add(tag.trim());
                        }
                        return List.copyOf(result);
                    }
                }
                """;
        } else throw new IllegalArgumentException("unsupported synthetic feature");
        Thread.sleep(450); // Makes the independently measured concurrent interval easy to observe.
        Path file = Path.of(name + ".java");
        Files.writeString(file, source);
        Path classes = Files.createTempDirectory(Path.of(System.getenv("TMPDIR")), "feature-");
        int code = ToolProvider.getSystemJavaCompiler().run(null, null, null, "-d", classes.toString(), file.toString());
        if (code != 0) throw new IllegalStateException("compile failed");
        try (var loader = new URLClassLoader(new java.net.URL[]{classes.toUri().toURL()}, ClassLoader.getPlatformClassLoader())) {
            var type = loader.loadClass(name);
            if (mode.equals("title")) {
                Object got = type.getMethod("normalize", String.class).invoke(null, " read ");
                if (!got.equals("read")) throw new IllegalStateException("title mismatch");
            } else {
                Object got = type.getMethod("normalize", List.class).invoke(null, List.of(" a ", "a", "B"));
                if (!got.equals(List.of("a", "B"))) throw new IllegalStateException("tags mismatch");
            }
        }
        System.out.println(mode.equals("title") ? "FEATURE_TITLE_OK" : "FEATURE_TAGS_OK");
    }
}
