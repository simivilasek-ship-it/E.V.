-- migrations/001_init_memory_graph.sql
CREATE TABLE IF NOT EXISTS entities (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  embedding TEXT,
  metadata TEXT
);

CREATE TABLE IF NOT EXISTS relations (
  id INTEGER PRIMARY KEY,
  subject_id INTEGER NOT NULL,
  predicate TEXT NOT NULL,
  object_id INTEGER NOT NULL,
  ts REAL NOT NULL,
  source TEXT,
  confidence REAL DEFAULT 1.0,
  FOREIGN KEY(subject_id) REFERENCES entities(id),
  FOREIGN KEY(object_id) REFERENCES entities(id)
);

CREATE INDEX IF NOT EXISTS idx_rel_subject_pred ON relations(subject_id, predicate);
CREATE INDEX IF NOT EXISTS idx_rel_object ON relations(object_id);
