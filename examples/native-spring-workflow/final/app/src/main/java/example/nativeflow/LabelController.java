package example.nativeflow;

import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/labels")
public class LabelController {
    private final LabelService service;

    public LabelController(LabelService service) {
        this.service = service;
    }

    @PostMapping("/normalize")
    public Labels normalize(@RequestBody Labels request) {
        return new Labels(service.normalize(request == null ? null : request.labels()));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Void> invalidLabels() {
        return ResponseEntity.badRequest().build();
    }

    public record Labels(List<String> labels) {
    }
}
