from __future__ import annotations

import unittest
from copy import deepcopy

from app.scripts.generate_season_practice import candidates, new_content, update, validate_generated


def sample_index(season_id="2026-09_2026-12", checked="2026-10-28"):
    return {
        "checkedAt": checked,
        "season": {"id": season_id, "start": season_id[:7] + "-01",
                   "months": [season_id[:7], "2026-10", "2026-11", "2026-12"]},
        "writing": [
            {"title": "Public transport and city access", "url": "https://example.org/w1",
             "month": "2026-10", "date": "2026-10-27", "task": "Task 2"},
            {"title": "Older topic", "url": "https://example.org/w2",
             "month": "2026-09", "date": "2026-09-03", "task": "Task 2"},
        ],
        "speaking": [
            {"title": "Local places", "url": "https://example.org/s1",
             "month": "2026-09", "part": "Part 1"},
            {"title": "A memorable journey", "url": "https://example.org/s2",
             "month": "2026-09", "part": "Part 2 / Part 3"},
        ],
    }


def sample_output(skill):
    if skill == "reading":
        paragraphs = [
            ("The invented town of Elmford is reviewing its bus routes. "
             "Residents asked for later evening services because the old timetable made visits to the library difficult. "
             "A local survey recorded their preferences, but planners also checked the cost of new vehicles. "
             "The council will trial a revised route during the autumn and publish passenger counts each week. ") * 2,
            ("The first proposal linked the station to a sports centre. "
             "Planners then added a hospital stop after speaking with older residents. "
             "The service will use smaller electric buses, which need a charging point near the depot. "
             "The trial budget includes driver training and signs at the new stops. ") * 2,
            ("Officials will compare journey times before deciding whether to keep the service. "
             "They will also invite comments from shop owners and passengers. "
             "A decision is expected after six months, when the town has enough observations to review costs and access. ") * 2,
        ]
        return {"title": "A fictional bus trial", "paragraphs": paragraphs,
                "questions": [{"prompt": "Which place was difficult to visit?", "answer": "library",
                               "explanation": "The opening paragraph names the library."}] * 5}
    if skill == "listening":
        sentences = [
            "Welcome to the fictional Elmford travel desk, where we can help you plan journeys around town this week.",
            "The new service begins at the station and continues towards the public library every twenty minutes.",
            "Passengers going to the hospital should remain on the same bus until the third stop after the bridge.",
            "A day ticket costs four pounds and can be purchased with a card at the machine beside the entrance.",
            "Please ask the driver for a printed timetable if the online display is difficult for you to read.",
            "On Saturday morning, the first bus leaves at seven thirty, which is earlier than the weekday service.",
            "The buses have space for one wheelchair, but folding bicycles must be stored beside the luggage rack.",
            "For a refund, visit the travel desk before Friday and bring the receipt from your original purchase.",
        ]
        return {"title": "A fictional travel announcement", "sentences": sentences,
                "questions": [{"prompt": "Where does the service begin?", "answer": "station",
                               "explanation": "The second sentence names the station."}] * 5}
    if skill == "writing":
        return {"title": "Access to transport", "prompt": "Some cities are considering a new public transport network to improve access for residents. Discuss the possible benefits and costs, and give your own opinion with reasons and examples.",
                "table": {"columns": [], "rows": []}}
    return {"title": "Local places", "questions": [
        "What kind of public place do you visit most often in your neighbourhood?",
        "How has that place changed since you first started going there?",
        "Would you like your neighbourhood to have more shared spaces in the future?",
    ]}


class GenerationTests(unittest.TestCase):
    def test_current_topics_create_four_practice_groups_once_per_check(self):
        index = sample_index()
        self.assertEqual(candidates(index, "writing")[0]["title"], "Public transport and city access")
        content, counts = update(index, new_content(index), lambda skill, _: sample_output(skill))
        self.assertEqual(counts, {"reading": 1, "listening": 1, "writing": 1, "speaking": 1})
        self.assertEqual(content["reading"][0]["sourceSkill"], "writing")
        self.assertIn("独立", content["listening"][0]["basis"])
        self.assertEqual(len(content["listening"][0]["sentenceAudio"]), 8)
        same, counts = update(index, content, lambda *_: self.fail("should not generate twice"))
        self.assertEqual(same, content)
        self.assertEqual(counts, {skill: 0 for skill in counts})

    def test_new_season_discards_all_old_practice(self):
        old_index = sample_index()
        old, _ = update(old_index, new_content(old_index), lambda skill, _: sample_output(skill))
        next_index = sample_index("2027-01_2027-04", "2027-01-01")
        next_index["season"]["months"] = ["2027-01", "2027-02", "2027-03", "2027-04"]
        next_index["writing"] = []
        next_index["speaking"] = []
        fresh, counts = update(next_index, old, lambda *_: self.fail("no new source"))
        self.assertEqual(fresh["seasonId"], "2027-01_2027-04")
        self.assertTrue(all(not fresh[skill] for skill in counts))

    def test_reject_answer_absent_from_text(self):
        index = sample_index()
        seed = candidates(index, "reading")[0]
        output = deepcopy(sample_output("reading"))
        output["questions"][0] = {"prompt": "What is the secret answer?", "answer": "unicorn",
                                  "explanation": "This is deliberately unsupported."}
        with self.assertRaisesRegex(ValueError, "not grounded"):
            validate_generated("reading", output, seed, index)


if __name__ == "__main__":
    unittest.main()
