package example.nativeflow;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
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
class ImplementationTest {
    @Autowired LabelService service;
    @Autowired MockMvc mvc;

    @Test
    void trimUsesJavaControlCharacterBoundaryAndPreservesInternalSpace() {
        assertEquals(List.of("a b", "ab"), service.normalize(List.of("\u0000\t A B \r\n", "AB")));
        assertThrows(IllegalArgumentException.class, () -> service.normalize(List.of("\t\r\n")));
    }

    @Test
    void whitespaceAboveTrimBoundaryIsPreservedThroughJson() throws Exception {
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                .content("{\"labels\":[\" \u00a0 \" ,\"\u2003BLUE\u2003\"]}"))
            .andExpect(status().isOk())
            .andExpect(content().json("{\"labels\":[\"\u00a0\",\"\u2003blue\u2003\"]}", true));
    }

    @Test
    void supplementaryCharactersAreCountedAsUtf16Units() {
        String emoji = "\ud83d\ude00";
        assertEquals(List.of(emoji.repeat(8)), service.normalize(List.of(emoji.repeat(8))));
        assertThrows(IllegalArgumentException.class, () -> service.normalize(List.of(emoji.repeat(9))));
    }

    @Test
    void lowercaseExpansionIsAcceptedExactlyAtLimitAndRejectedAboveIt() {
        assertEquals(List.of("i\u0307".repeat(8)), service.normalize(List.of("\u0130".repeat(8))));
        assertThrows(IllegalArgumentException.class, () -> service.normalize(List.of("\u0130".repeat(9))));
    }

    @Test
    void immutableInputAndRepeatedCallsRetainOrderWithoutSharedState() {
        List<String> input = List.of(" D ", "C", "b", "A", "d", " C ");
        assertEquals(List.of("d", "c", "b", "a"), service.normalize(input));
        assertEquals(List.of("z"), service.normalize(List.of(" Z ")));
        assertEquals(List.of("d", "c", "b", "a"), service.normalize(input));
        assertEquals(List.of(" D ", "C", "b", "A", "d", " C "), input);
    }

    @Test
    void rejectionAfterValidPrefixLeavesCallerInputUntouched() {
        List<List<String>> invalidInputs = List.of(
                Arrays.asList(" A ", null),
                List.of(" A ", "  "),
                List.of(" A ", "x".repeat(17)),
                List.of(" A ", "b", "c", "d", "e"));
        for (List<String> invalid : invalidInputs) {
            var input = new ArrayList<>(invalid);
            var before = new ArrayList<>(input);
            assertThrows(IllegalArgumentException.class, () -> service.normalize(input));
            assertEquals(before, input);
        }
    }

    @Test
    void rejectedHttpRequestDoesNotLeakPartialResultsIntoNextCall() throws Exception {
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                .content("{\"labels\":[\"a\",\"b\",\"c\",\"d\",\"e\"]}"))
            .andExpect(status().isBadRequest());
        mvc.perform(post("/labels/normalize").contentType(MediaType.APPLICATION_JSON)
                .content("{\"labels\":[\" New \"]}"))
            .andExpect(status().isOk()).andExpect(content().json("{\"labels\":[\"new\"]}", true));
    }
}
