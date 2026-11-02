package example.nativeflow;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(classes = DemoApplication.class, webEnvironment = SpringBootTest.WebEnvironment.MOCK)
@AutoConfigureMockMvc
class IndependentVerificationTest {
    @Autowired LabelService service;
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;

    @Test
    void everyCharacterThroughU0020IsTrimmedAndAnEmptyResultIsRejected() throws Exception {
        for (int codeUnit = 0; codeUnit <= 0x20; codeUnit++) {
            String edge = String.valueOf((char) codeUnit);
            var input = new ArrayList<>(List.of(edge + "BlUe" + edge));
            var before = new ArrayList<>(input);
            assertEquals(List.of("blue"), service.normalize(input), "trim boundary " + codeUnit);
            assertEquals(before, input, "caller input at boundary " + codeUnit);
            expectLabels(input, List.of("blue"));
            mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                    .content(request(List.of("ok", edge))))
                .andExpect(status().isBadRequest());
        }
    }

    @Test
    void unicodeContextAndCanonicalDifferencesRemainStringDifferences() throws Exception {
        // ROOT lowercasing maps capital final sigma contextually; it does not case-fold
        // ordinary sigma into final sigma or canonically compose a combining accent.
        List<String> input = List.of("ΟΣ", "οσ", "ος", " É ", "e\u0301");
        List<String> expected = List.of("ος", "οσ", "é", "e\u0301");
        assertEquals(expected, service.normalize(input));
        expectLabels(input, expected);
    }

    @Test
    void manyDuplicatesIncludingExpandedLowercaseDoNotUseDistinctSlots() throws Exception {
        var input = new ArrayList<String>();
        for (int repetition = 0; repetition < 25; repetition++) {
            input.addAll(List.of(" İ ", "i\u0307", " Q ", "q", "B", " A "));
        }
        var before = new ArrayList<>(input);
        List<String> expected = List.of("i\u0307", "q", "b", "a");
        assertEquals(expected, service.normalize(input));
        expectLabels(input, expected);
        assertEquals(before, input);
    }

    @Test
    void lateInvalidItemsAfterFourLabelsRejectWithoutChangingCallerOrNextRequest() throws Exception {
        for (String invalid : Arrays.asList(null, "\u0000\t ", "x".repeat(17), "İ".repeat(9), "fifth")) {
            var input = new ArrayList<>(List.of(" D ", "C", "b", "A", " d "));
            input.add(invalid);
            var before = new ArrayList<>(input);
            // The service exception class is not part of the public contract.
            assertThrows(RuntimeException.class, () -> service.normalize(input));
            assertEquals(before, input);
            mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                    .content(request(input)))
                .andExpect(status().isBadRequest());
            expectLabels(List.of(" Fresh "), List.of("fresh"));
            assertEquals(before, input);
        }
    }

    @Test
    void mixedSupplementaryCharactersAndLowercaseExpansionUseFinalUtf16Length() throws Exception {
        String prefix = "\ud83d\ude00".repeat(7);
        expectLabels(List.of(" " + prefix + "İ "), List.of(prefix + "i\u0307"));
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                .content(request(List.of("ok", prefix + "xİ"))))
            .andExpect(status().isBadRequest());
    }

    private String request(List<String> labels) throws Exception {
        return json.writeValueAsString(Map.of("labels", labels));
    }

    private void expectLabels(List<String> input, List<String> expected) throws Exception {
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                .content(request(input)))
            .andExpect(status().isOk())
            .andExpect(content().json(request(expected), true));
    }
}
