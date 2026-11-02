package example.nativeflow;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest(classes = DemoApplication.class, webEnvironment = SpringBootTest.WebEnvironment.MOCK)
@AutoConfigureMockMvc
class LabelContractTest {
    @Autowired MockMvc mvc;
    @Autowired LabelService service;

    @Test void springBeanAndControllerAreWired() throws Exception {
        assertNotNull(service);
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                .content("{\"labels\":[\"Blue\"]}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.labels[0]").value("blue"));
    }
    @Test void trimCaseAndStableDeduplication() throws Exception {
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                .content("{\"labels\":[\" Green \",\"BLUE\",\"green\",\" blue \" ]}"))
            .andExpect(status().isOk()).andExpect(content().json("{\"labels\":[\"green\",\"blue\"]}", true));
    }
    @Test void emptyListIsValid() throws Exception {
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON).content("{\"labels\":[]}"))
            .andExpect(status().isOk()).andExpect(content().json("{\"labels\":[]}", true));
    }
    @Test void nullListIsRejected() throws Exception {
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON).content("{\"labels\":null}"))
            .andExpect(status().isBadRequest());
    }
    @Test void nullItemIsRejected() throws Exception {
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON).content("{\"labels\":[\"ok\",null]}"))
            .andExpect(status().isBadRequest());
    }
    @Test void blankItemRejectsWholeRequest() throws Exception {
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON).content("{\"labels\":[\"ok\",\"  \"]}"))
            .andExpect(status().isBadRequest());
    }
    @Test void exactlySixteenCharactersAreAccepted() throws Exception {
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                .content("{\"labels\":[\"  ABCDEFGHIJKLMNOP  \"]}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.labels[0]").value("abcdefghijklmnop"));
    }
    @Test void seventeenCharactersAreRejected() throws Exception {
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                .content("{\"labels\":[\"abcdefghijklmnopq\"]}"))
            .andExpect(status().isBadRequest());
    }
    @Test void duplicatesDoNotConsumeDistinctLimit() throws Exception {
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                .content("{\"labels\":[\"A\",\" a \",\"b\",\"c\",\"d\",\"D\"]}"))
            .andExpect(status().isOk()).andExpect(content().json("{\"labels\":[\"a\",\"b\",\"c\",\"d\"]}", true));
    }
    @Test void fifthDistinctLabelIsRejected() throws Exception {
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                .content("{\"labels\":[\"a\",\"b\",\"c\",\"d\",\"e\"]}"))
            .andExpect(status().isBadRequest());
    }
    @Test void rootLocaleSurvivesTurkishDefault() throws Exception {
        Locale previous = Locale.getDefault();
        try {
            Locale.setDefault(Locale.forLanguageTag("tr-TR"));
            mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                    .content("{\"labels\":[\"I\"]}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.labels[0]").value("i"));
        } finally { Locale.setDefault(previous); }
    }
    @Test void lengthIsCheckedAfterRootLowercase() throws Exception {
        // U+0130 expands to i + combining dot under Locale.ROOT.
        String input = "\u0130".repeat(16);
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                .content("{\"labels\":[\"" + input + "\"]}"))
            .andExpect(status().isBadRequest());
    }
    @Test void callerInputListIsNotMutated() {
        var input = new ArrayList<>(List.of(" Blue ", "BLUE", "green"));
        var before = List.copyOf(input);
        assertEquals(List.of("blue", "green"), service.normalize(input));
        assertEquals(before, input);
    }
}
