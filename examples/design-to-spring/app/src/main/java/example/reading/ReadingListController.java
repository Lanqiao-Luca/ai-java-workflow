package example.reading;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/lists")
public class ReadingListController {
    private final ReadingListService service;
    public ReadingListController(ReadingListService service) { this.service = service; }

    @GetMapping("/{id}")
    public ReadingListService.Snapshot read(@PathVariable String id, @RequestHeader("X-Actor") String actor) {
        return service.read(id, actor);
    }

    @PostMapping("/{id}/archive")
    public ReadingListService.Snapshot archive(@PathVariable String id, @RequestHeader("X-Actor") String actor,
                                               @RequestBody ReadingListService.ArchiveRequest request) {
        return service.archive(id, actor, request);
    }
}
