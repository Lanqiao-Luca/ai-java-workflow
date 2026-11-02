package example.graph;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
@SpringBootTest @AutoConfigureMockMvc
class IntegrationTest {
 @org.junit.jupiter.api.BeforeAll static void identity() { System.out.println("BUILD_TEST_JVM="+ProcessHandle.current().pid()); }
 @Autowired MockMvc mvc;
 @Test void bothRoutes() throws Exception {
  mvc.perform(get("/title").param("value"," Comet ")).andExpect(content().string("Comet"));
  mvc.perform(get("/tags").param("value","x,y,x")).andExpect(content().string("x,y"));
 }
 @Test void independentRequests() throws Exception {
  mvc.perform(get("/title").param("value","A")).andExpect(content().string("A"));
  mvc.perform(get("/title").param("value","B")).andExpect(content().string("B"));
 }
}
