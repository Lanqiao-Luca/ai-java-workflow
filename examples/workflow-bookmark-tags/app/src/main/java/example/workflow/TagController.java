package example.workflow;

import java.util.List;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
public class TagController {
    public record Request(Long expectedVersion, List<String> tags) { }
    private final TagService service;
    public TagController(TagService service) { this.service = service; }

    /** X-Demo-Actor is a synthetic fixture identity, never a production auth mechanism. */
    @PutMapping("/bookmarks/{id}/tags")
    public TagService.Bookmark replace(@PathVariable String id,
            @RequestHeader("X-Demo-Actor") String actor, @RequestBody Request body) {
        return service.replace(id, actor, body.expectedVersion(), body.tags());
    }
}

@RestControllerAdvice
class DemoErrors {
    @ExceptionHandler(TagService.Rejected.class)
    ResponseEntity<Map<String, String>> rejected(TagService.Rejected problem) {
        return ResponseEntity.status(problem.status()).body(Map.of("code", problem.code()));
    }
}
