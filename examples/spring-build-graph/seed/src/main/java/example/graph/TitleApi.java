package example.graph;
import org.springframework.web.bind.annotation.*;
@RestController public class TitleApi {
 @GetMapping("/title") public String title(@RequestParam("value") String value) { return "pending"; }
}
