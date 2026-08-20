import argparse
import json
from pathlib import Path

from interview_intelligence.domain.models import TranscriptSegment
from interview_intelligence.quality.detector import TranscriptQualityDetector


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan transcript segments for obvious hallucination/repetition patterns."
    )
    parser.add_argument("segments_json", type=Path)
    args = parser.parse_args()

    raw = json.loads(args.segments_json.read_text(encoding="utf-8"))
    segments = [TranscriptSegment.model_validate(item) for item in raw]

    issues = TranscriptQualityDetector().detect(segments)

    payload = {
        "segment_count": len(segments),
        "issue_count": len(issues),
        "issues": [issue.model_dump(mode="json") for issue in issues],
    }

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
