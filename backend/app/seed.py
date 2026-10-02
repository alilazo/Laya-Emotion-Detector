"""Optional, clearly labeled illustrative data for presenting the constellation."""

import argparse
import json
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from .config import Settings
from .db import Database
from .gauge import EMOTIONS, update_gauges

SAMPLES = [
    (
        "Before the interview",
        [
            ("I keep thinking about tomorrow's interview.", (66, 0, 8)),
            ("What if I forget everything?", (89, 2, 17)),
            ("I still feel nervous, but I made a plan.", (58, 0, 4)),
        ],
    ),
    (
        "The empty house",
        [
            ("I really miss my dog today.", (3, 72, 1)),
            ("The house feels empty without him.", (2, 92, 0)),
            ("I found a photo and cried again.", (0, 82, 0)),
        ],
    ),
    (
        "Late walk home",
        [
            ("A stranger followed me on the walk home.", (36, 0, 65)),
            ("I thought they were still behind me and felt terrified.", (67, 2, 96)),
            ("I'm home now, but I still feel on edge.", (50, 0, 36)),
        ],
    ),
    (
        "A difficult goodbye",
        [
            ("My friend moved away and I feel lonely.", (13, 74, 1)),
            ("I worry we won't stay close.", (58, 56, 0)),
            ("I miss our usual evenings together.", (12, 82, 0)),
        ],
    ),
    (
        "Storm warning",
        [
            ("The storm warning has me worried about the roof.", (69, 8, 43)),
            ("The wind is loud and I feel scared.", (75, 3, 83)),
            ("The weather has calmed down a little.", (19, 0, 28)),
        ],
    ),
    (
        "Weekend plans",
        [
            ("I made a list of places to visit this weekend.", (0, 0, 0)),
            ("We booked tickets and picked a cafe.", (0, 0, 0)),
            ("I'm looking forward to it.", (0, 0, 0)),
        ],
    ),
    (
        "Waiting for news",
        [
            ("I haven't heard back and the uncertainty is hard.", (61, 23, 11)),
            ("I keep replaying everything I said.", (79, 37, 5)),
            ("I'm disappointed and still waiting.", (51, 64, 0)),
        ],
    ),
    (
        "The old photograph",
        [
            ("I found a picture of my grandfather.", (0, 34, 0)),
            ("I miss him so much today.", (0, 88, 0)),
            ("It brought back some good memories too.", (0, 49, 0)),
        ],
    ),
    (
        "Noise at the door",
        [
            ("Someone keeps trying the front door.", (49, 1, 76)),
            ("I am scared they might get inside.", (77, 2, 98)),
            ("It stopped, but I still feel shaken.", (41, 3, 65)),
        ],
    ),
    (
        "A quiet Monday",
        [
            ("I watered the plants this morning.", (0, 0, 0)),
            ("Then I finished some paperwork.", (0, 0, 0)),
            ("I might cook dinner later.", (0, 0, 0)),
        ],
    ),
    (
        "Moving day",
        [
            ("I'm sad to leave this place and nervous about the move.", (54, 61, 7)),
            ("The new street feels unfamiliar at night.", (46, 48, 41)),
            ("I found my favorite things in the boxes.", (10, 25, 0)),
        ],
    ),
    (
        "An uncertain call",
        [
            ("I dread the call tomorrow and feel scared of what I'll hear.", (83, 17, 68)),
            ("I keep thinking about every possible outcome.", (93, 24, 43)),
            ("I hope I can rest tonight.", (59, 18, 19)),
        ],
    ),
]


def seed(db: Database) -> int:
    db.initialize()
    count = 0
    for index, (title, turns) in enumerate(SAMPLES):
        chat_id = str(uuid5(NAMESPACE_URL, f"emotion-constellation-illustrative/{title}"))
        created = datetime.now(UTC) - timedelta(days=index * 2 + 1)
        stamps = [(created + timedelta(minutes=step)).isoformat() for step in range(len(turns))]
        previous = {key: 0.0 for key in EMOTIONS}
        peak = previous.copy()
        totals = previous.copy()
        with db.connection() as conn:
            if conn.execute("SELECT 1 FROM chats WHERE id=?", (chat_id,)).fetchone():
                continue
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO chats(id,title,source,created_at,updated_at) VALUES(?,?,?,?,?)",
                    (chat_id, title, "illustrative", stamps[0], stamps[-1]),
                )
                for step, (text, instant_tuple) in enumerate(turns):
                    instant = dict(zip(EMOTIONS, instant_tuple))
                    after = update_gauges(previous, instant, first=step == 0)
                    sequence = step * 2 + 1
                    message_id = str(uuid5(NAMESPACE_URL, f"{chat_id}/{sequence}"))
                    conn.execute(
                        "INSERT INTO messages(id,chat_id,sequence_number,role,content,emotion_status,created_at) VALUES(?,?,?,?,?,?,?)",
                        (message_id, chat_id, sequence, "user", text, "ready", stamps[step]),
                    )
                    conn.execute(
                        "INSERT INTO messages(id,chat_id,sequence_number,role,content,emotion_status,created_at) VALUES(?,?,?,?,?,?,?)",
                        (
                            str(uuid5(NAMESPACE_URL, f"{chat_id}/{sequence + 1}")),
                            chat_id,
                            sequence + 1,
                            "assistant",
                            "This is an illustrative showcase conversation.",
                            "not_applicable",
                            stamps[step],
                        ),
                    )
                    conn.execute(
                        "INSERT INTO emotion_snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            str(uuid5(NAMESPACE_URL, f"snapshot/{message_id}")),
                            chat_id,
                            message_id,
                            sequence,
                            "illustrative",
                            "illustrative-v1",
                            *(instant[key] / 25 for key in EMOTIONS),
                            *(instant[key] for key in EMOTIONS),
                            *(previous[key] for key in EMOTIONS),
                            *(after[key] for key in EMOTIONS),
                            json.dumps({}),
                            stamps[step],
                        ),
                    )
                    for key in EMOTIONS:
                        peak[key] = max(peak[key], after[key])
                        totals[key] += after[key]
                    previous = after
                updates = {f"current_{key}": previous[key] for key in EMOTIONS}
                updates.update({f"peak_{key}": peak[key] for key in EMOTIONS})
                updates.update({f"average_{key}": totals[key] / len(turns) for key in EMOTIONS})
                conn.execute(
                    f"UPDATE chats SET {', '.join(f'{key}=?' for key in updates)}, emotion_message_count=? WHERE id=?",
                    (*updates.values(), len(turns), chat_id),
                )
                conn.execute("COMMIT")
                count += 1
            except Exception:
                conn.execute("ROLLBACK")
                raise
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=None)
    arguments = parser.parse_args()
    settings = Settings()
    from pathlib import Path

    path = Path(arguments.database) if arguments.database else settings.database_path
    print(f"Added {seed(Database(path))} illustrative chats to {path}")
