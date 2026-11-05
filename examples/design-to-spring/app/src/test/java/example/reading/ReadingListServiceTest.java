package example.reading;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;
import static org.junit.jupiter.api.Assertions.*;

class ReadingListServiceTest {
    private final ReadingListService service = new ReadingListService();
    private ReadingListService.Snapshot read() { return service.read("reading", "demo-owner"); }
    private ReadingListService.Snapshot archive(List<String> ids, Long version) {
        return service.archive("reading", "demo-owner", new ReadingListService.ArchiveRequest(ids, version));
    }

    @Test void validBatchChangesExactlyOneVersionAndKeepsTitlesOrder() {
        var result = archive(List.of("b", "a"), 1L);
        assertEquals(2, result.version());
        assertEquals(List.of("Alpha", "Beta", "Gamma"), result.items().stream().map(ReadingListService.Item::title).toList());
        assertTrue(result.items().stream().allMatch(ReadingListService.Item::archived));
    }
    @Test void invalidTailDoesNotPartiallyArchive() {
        var before = read();
        var error = assertThrows(ResponseStatusException.class, () -> archive(Arrays.asList("a", null), 1L));
        assertEquals(400, error.getStatusCode().value());
        assertEquals(before, read());
    }
    @Test void unknownTailDoesNotPartiallyArchive() {
        var before = read();
        assertEquals(404, assertThrows(ResponseStatusException.class, () -> archive(List.of("a", "missing"), 1L)).getStatusCode().value());
        assertEquals(before, read());
    }
    @Test void ownerCheckedBeforeBusinessPayloadOrVersion() {
        var before = read();
        var error = assertThrows(ResponseStatusException.class, () -> service.archive("reading", "other", null));
        assertEquals(403, error.getStatusCode().value());
        assertEquals(before, read());
    }
    @Test void nullVersionNullIdsEmptyAndBlankRejectWithoutChange() {
        var before = read();
        for (var request : List.of(new ReadingListService.ArchiveRequest(List.of("a"), null),
                new ReadingListService.ArchiveRequest(null, 1L), new ReadingListService.ArchiveRequest(List.of(), 1L),
                new ReadingListService.ArchiveRequest(List.of(" "), 1L))) {
            assertEquals(400, assertThrows(ResponseStatusException.class, () -> service.archive("reading", "demo-owner", request)).getStatusCode().value());
            assertEquals(before, read());
        }
    }
    @Test void duplicatesDoNotChangeCallerOrIncrementTwice() {
        var ids = new ArrayList<>(List.of("a", "a"));
        assertEquals(2, archive(ids, 1L).version());
        assertEquals(List.of("a", "a"), ids);
    }
    @Test void currentVersionNoopPreservesSnapshot() {
        var before = read();
        assertEquals(before, archive(List.of("c"), 1L));
    }
    @Test void staleNoopRejectsAndPreservesSnapshot() {
        var before = read();
        assertEquals(409, assertThrows(ResponseStatusException.class, () -> archive(List.of("c"), 0L)).getStatusCode().value());
        assertEquals(before, read());
    }
    @Test void snapshotsAreImmutable() {
        assertThrows(UnsupportedOperationException.class, () -> read().items().clear());
    }
    @Test void concurrentOldVersionWritersCannotBothCommit() throws Exception {
        var pool = Executors.newFixedThreadPool(2);
        var ready = new CountDownLatch(2);
        var go = new CountDownLatch(1);
        try {
            var futures = new ArrayList<java.util.concurrent.Future<Integer>>();
            for (String id : List.of("a", "b")) futures.add(pool.submit(() -> {
                ready.countDown();
                if (!go.await(5, TimeUnit.SECONDS)) throw new AssertionError("start barrier timed out");
                try { archive(List.of(id), 1L); return 200; }
                catch (ResponseStatusException error) { return error.getStatusCode().value(); }
            }));
            assertTrue(ready.await(5, TimeUnit.SECONDS)); go.countDown();
            var results = new ArrayList<Integer>();
            for (var future : futures) results.add(future.get(5, TimeUnit.SECONDS));
            results.sort(Integer::compareTo);
            assertEquals(List.of(200, 409), results);
            assertEquals(2, read().version());
            assertEquals(2, read().items().stream().filter(ReadingListService.Item::archived).count());
        } finally { go.countDown(); pool.shutdownNow(); assertTrue(pool.awaitTermination(5, TimeUnit.SECONDS)); }
    }
}
