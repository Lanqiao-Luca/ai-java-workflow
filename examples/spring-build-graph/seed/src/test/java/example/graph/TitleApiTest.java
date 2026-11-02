package example.graph;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
@SpringBootTest @AutoConfigureMockMvc
class TitleApiTest {
 @org.junit.jupiter.api.BeforeAll static void identity() { System.out.println("BUILD_TEST_JVM="+ProcessHandle.current().pid()); }
 @Autowired MockMvc mvc;
 @Test void trim() throws Exception { Thread.sleep(300); mvc.perform(get("/title").param("value","  Nebula  ")).andExpect(status().isOk()).andExpect(content().string("Nebula")); }
 @Test void blank() throws Exception { mvc.perform(get("/title").param("value","  ")).andExpect(status().isBadRequest()); }
 @Test void missing() throws Exception { mvc.perform(get("/title")).andExpect(status().isBadRequest()); }
}
