package example.reading;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_EACH_TEST_METHOD)
class ReadingListWebTest {
    @Autowired MockMvc mvc;
    @Test void realContextGetSerializesVersionAndOrderedItems() throws Exception {
        mvc.perform(get("/lists/reading").header("X-Actor", "demo-owner"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.version").value(1))
            .andExpect(jsonPath("$.items[0].title").value("Alpha")).andExpect(jsonPath("$.items[2].archived").value(true));
    }
    @Test void postArchivesThroughRealControllerAndService() throws Exception {
        mvc.perform(post("/lists/reading/archive").header("X-Actor", "demo-owner").contentType("application/json")
            .content("{\"ids\":[\"a\",\"b\"],\"version\":1}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.version").value(2)).andExpect(jsonPath("$.items[0].archived").value(true));
    }
    @Test void rejectedWebBatchLeavesEntireSnapshotUnchanged() throws Exception {
        mvc.perform(post("/lists/reading/archive").header("X-Actor", "demo-owner").contentType("application/json")
            .content("{\"ids\":[\"a\",null],\"version\":1}"))
            .andExpect(status().isBadRequest());
        mvc.perform(get("/lists/reading").header("X-Actor", "demo-owner"))
            .andExpect(jsonPath("$.version").value(1)).andExpect(jsonPath("$.items[0].archived").value(false));
    }
    @Test void forbiddenAndStaleStatusesAreMapped() throws Exception {
        mvc.perform(post("/lists/reading/archive").header("X-Actor", "other").contentType("application/json")
            .content("{\"ids\":null,\"version\":0}")).andExpect(status().isForbidden());
        mvc.perform(post("/lists/reading/archive").header("X-Actor", "demo-owner").contentType("application/json")
            .content("{\"ids\":[\"c\"],\"version\":0}")).andExpect(status().isConflict());
    }
}
