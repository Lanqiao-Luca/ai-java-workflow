import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import javax.tools.ToolProvider;

/** Merge validation compiles and tests both Workflow outputs in a single foreground JVM. */
class Integration {
    public static void main(String[] args) throws Exception {
        Path classes = Files.createTempDirectory(Path.of(System.getenv("TMPDIR")), "integration-");
        int code = ToolProvider.getSystemJavaCompiler().run(null, null, null, "-d", classes.toString(),
            "TitlePolicy.java", "TagPolicy.java", "GraphAssertions.java");
        if (code != 0) throw new IllegalStateException("combined source does not compile");
        try (var loader = new URLClassLoader(new java.net.URL[]{classes.toUri().toURL()}, ClassLoader.getPlatformClassLoader())) {
            loader.loadClass("GraphAssertions").getMethod("main", String[].class).invoke(null, (Object)new String[0]);
        }
    }
}
