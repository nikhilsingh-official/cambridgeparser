# Generated Resources

This directory is the default home for parser-created artifacts that the website
frontend reads.

- `normalized_marker_output/`: Marker layout output scaled to OCR image coordinates.
- `qp_output/`: question-paper hierarchies and segmented question records.
- `ms_output/`: parsed mark-scheme hierarchies and marking data.
- `pseudocode_writing_hits/`: selected pseudocode-writing records, screenshots, extracted marking points, validations, and grading eval outputs.

The generated subdirectories are ignored by Git; keep only small fixtures in
`tests/` when a test needs sample data.
