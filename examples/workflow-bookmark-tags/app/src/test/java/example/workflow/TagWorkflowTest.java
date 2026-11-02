package example.workflow;

import java.util.Arrays;
import java.util.List;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK)
@AutoConfigureMockMvc
class TagWorkflowTest {
    @Autowired MockMvc mvc;
    @Autowired TagService service;
    @Autowired ObjectMapper mapper;
    @BeforeEach void resetFixture() { service.reset(); }

    private org.springframework.test.web.servlet.ResultActions request(String id, String actor,
            Long version, List<String> tags) throws Exception {
        return mvc.perform(put("/bookmarks/" + id + "/tags").header("X-Demo-Actor", actor)
            .contentType(MediaType.APPLICATION_JSON)
            .content(mapper.writeValueAsBytes(new TagController.Request(version, tags))));
    }
    private void unchanged(TagService.Bookmark previous, int count) {
        assertThat(service.get("demo")).isEqualTo(previous);
        assertThat(service.auditCount()).isEqualTo(count);
    }
    @Test void contextWiresRealServiceAndController() {
        assertThat(mvc).isNotNull(); assertThat(service).isNotNull();
    }
    @Test void normalizeDeduplicateAndPersist() throws Exception {
        var previous = service.get("demo");
        request("demo", "reader-demo", 0L, List.of(" read ", "read", "Read"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.tags[0]").value("read"))
            .andExpect(jsonPath("$.tags[1]").value("Read"));
        var stored = service.get("demo");
        assertThat(stored.tags()).containsExactly("read", "Read");
        assertThat(stored.owner()).isEqualTo(previous.owner());
        assertThat(stored.title()).isEqualTo(previous.title());
        assertThat(stored.savedSequence()).isEqualTo(previous.savedSequence());
        assertThat(stored.version()).isEqualTo(1); assertThat(service.auditCount()).isEqualTo(1);
    }
    @Test void emptyListClearsTags() throws Exception {
        request("demo", "reader-demo", 0L, List.of()).andExpect(status().isOk());
        assertThat(service.get("demo").tags()).isEmpty();
        assertThat(service.get("demo").version()).isEqualTo(1);
        assertThat(service.auditCount()).isEqualTo(1);
    }
    @Test void nullListRejectsWithoutMutation() throws Exception {
        var old = service.get("demo");
        request("demo", "reader-demo", 0L, null).andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.code").value("MISSING_TAGS")); unchanged(old, 0);
    }
    @Test void blankItemRejectsWholeRequest() throws Exception {
        var old = service.get("demo");
        request("demo", "reader-demo", 0L, List.of("ok", "  "))
            .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("INVALID_TAG"));
        unchanged(old, 0);
    }
    @Test void nullItemRejectsWholeRequest() throws Exception {
        var old = service.get("demo");
        request("demo", "reader-demo", 0L, Arrays.asList("ok", null))
            .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("INVALID_TAG"));
        unchanged(old, 0);
    }
    @Test void nonOwnerRejectsBeforeTagValidation() throws Exception {
        var old = service.get("demo");
        request("demo", "other-demo", 0L, null).andExpect(status().isForbidden())
            .andExpect(jsonPath("$.code").value("NOT_OWNER")); unchanged(old, 0);
    }
    @Test void staleVersionRejectsWithoutMutation() throws Exception {
        var old = service.get("demo");
        request("demo", "reader-demo", 9L, List.of("new")).andExpect(status().isConflict())
            .andExpect(jsonPath("$.code").value("STALE_VERSION")); unchanged(old, 0);
    }
    @Test void missingVersionRejects() throws Exception {
        var old = service.get("demo");
        request("demo", "reader-demo", null, List.of()).andExpect(status().isBadRequest()); unchanged(old, 0);
    }
    @Test void missingReferenceRejects() throws Exception {
        var old = service.get("demo");
        request("missing", "reader-demo", 0L, List.of()).andExpect(status().isNotFound()); unchanged(old, 0);
    }
    @Test void normalizedNoopPreservesVersionAndAudit() throws Exception {
        var old = service.get("demo");
        request("demo", "reader-demo", 0L, List.of(" old ", "old")).andExpect(status().isOk()); unchanged(old, 0);
    }
    @Test void repeatAtCurrentVersionIsNoop() throws Exception {
        request("demo", "reader-demo", 0L, List.of("new")).andExpect(status().isOk());
        var old = service.get("demo");
        request("demo", "reader-demo", 1L, List.of(" new ")).andExpect(status().isOk()); unchanged(old, 1);
    }
    @Test void staleRetryAfterSuccessRejects() throws Exception {
        request("demo", "reader-demo", 0L, List.of("new")).andExpect(status().isOk());
        var old = service.get("demo");
        request("demo", "reader-demo", 0L, List.of("again")).andExpect(status().isConflict()); unchanged(old, 1);
    }
}
