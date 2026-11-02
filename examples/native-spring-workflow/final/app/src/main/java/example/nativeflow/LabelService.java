package example.nativeflow;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import org.springframework.stereotype.Service;

@Service
public class LabelService {
    public List<String> normalize(List<String> labels) {
        if (labels == null) {
            throw new IllegalArgumentException("Labels must not be null");
        }

        var normalized = new LinkedHashSet<String>();
        for (String label : labels) {
            if (label == null) {
                throw new IllegalArgumentException("Label must not be null");
            }
            String value = label.trim().toLowerCase(Locale.ROOT);
            if (value.isEmpty() || value.length() > 16) {
                throw new IllegalArgumentException("Label must contain 1 to 16 UTF-16 code units");
            }
            normalized.add(value);
            if (normalized.size() > 4) {
                throw new IllegalArgumentException("At most four distinct labels are allowed");
            }
        }
        return List.copyOf(normalized);
    }
}
