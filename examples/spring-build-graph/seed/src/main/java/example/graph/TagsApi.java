package example.graph;
import org.springframework.web.bind.annotation.*;
@RestController public class TagsApi {
 @GetMapping("/tags") public String tags(@RequestParam("value") String value) { return "pending"; }
}
