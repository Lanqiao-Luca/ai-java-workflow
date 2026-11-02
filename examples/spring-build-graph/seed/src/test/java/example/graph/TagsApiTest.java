package example.graph;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
@SpringBootTest @AutoConfigureMockMvc
class TagsApiTest {
 @org.junit.jupiter.api.BeforeAll static void identity() { System.out.println("BUILD_TEST_JVM="+ProcessHandle.current().pid()); }
 @Autowired MockMvc mvc;
 @Test void distinct() throws Exception { Thread.sleep(300); mvc.perform(get("/tags").param("value"," blue,green,blue ")).andExpect(status().isOk()).andExpect(content().string("blue,green")); }
 @Test void blankElement() throws Exception { mvc.perform(get("/tags").param("value","blue, ")).andExpect(status().isBadRequest()); }
 @Test void preserveCase() throws Exception { mvc.perform(get("/tags").param("value","Blue,blue")).andExpect(content().string("Blue,blue")); }
}
