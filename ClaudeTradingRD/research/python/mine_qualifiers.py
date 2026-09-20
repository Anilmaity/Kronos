"""Mine narrated accept/reject calls for the corpus's undefined qualitative terms.

Why this exists
---------------
`meta/automation_gaps.md` shows that a handful of undefined adjectives gate ~100
concepts: displacement / "aggressive" (37+34), "small wick" / "large wick"
(13+11), "shallow" (23), "strong" (26). RESUME.md finding #5 records that no
number is stated for any of them anywhere in 443 videos -- a *settled negative*.
They therefore have to be FIT, not found.

The only supervision signal available is that the author repeatedly narrates a
verdict while pointing at a specific candle: "this would form too large of a
wick for an expansion candle", "is this a shallow run? No, this is a large
opposing run". Each such utterance is a weak label. This script harvests them.

What it produces
----------------
- meta/qualifier_calls.json : machine-readable. Two sections --
    `candidates` (every regex hit, with an *automatic* polarity guess) and
    `curated`   (the hand-reviewed subset; see CURATION below).
- meta/qualifier_calls.md   : the human-readable curated table + a candidate
                              digest ranked by narration score.

Honesty constraints baked in
----------------------------
1. Transcripts are flattened auto-captions. Punctuation is unreliable and in
   several files absent entirely (1oco9lesido has zero periods in 1,812 chars),
   so context windows are WORD-based, not sentence-based. The automatic
   ACCEPT/REJECT guess is a heuristic and is reported as such -- its agreement
   with the hand review is printed so the reader can see the precision.
2. `Nlw-PZhoViQ` was recovered by local ASR (`transcript_source: whisper-*`)
   which mangles domain jargon. Any hit from an ASR file is flagged `asr: true`
   and is excluded from the curated set.
3. Every curated quote is checked to be <= 15 words AND present verbatim in the
   transcript file, matching the rule `python/validate_concepts.py` enforces on
   concept files. The script refuses to write if a quote fails.

Run:  python mine_qualifiers.py            (from research/python or research/)
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, asdict, field
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
TRANSCRIPTS = RESEARCH / "raw" / "transcripts"
META = RESEARCH / "meta"
SEP = "-" * 70

WINDOW_WORDS = 45          # +/- words of context kept around a hit
POLARITY_WORDS = 14        # +/- words searched for a polarity cue


# ── term families ─────────────────────────────────────────────────────────────
# Each family is a list of regexes. Kept deliberately narrow: broad patterns
# (bare "strong", bare "big") drown the signal in prose that is not a chart call.
TERM_PATTERNS: dict[str, list[str]] = {
    "wick_size": [
        r"\b(small|large|larger|big|bigger|huge|tiny|little|long|longer|shallow|deep)\s+"
        r"(opposing\s+)?wick\b",
        r"\bwick\s+(is|was)\s+(too\s+)?(small|large|larger|big|bigger|huge|tiny|little|long)\b",
        r"\btoo\s+(large|big|much)\s+of\s+a\s+wick\b",
        r"\bwick\s+(is|was)\s+(larger|smaller|bigger)\s+than\s+the\s+body\b",
        r"\b(no|without\s+a|barely\s+a|hardly\s+a)\s+wick\b",
    ],
    "displacement": [
        r"\bdisplacement\b",
        r"\bdisplac(e|es|ed|ing)\b",
    ],
    "aggressive": [
        r"\baggressive(ly)?\b",
        r"\baggression\b",
        r"\benergetic(ally)?\b",
    ],
    "shallow": [
        r"\bshallow\b",
        r"\bdeep\s+(retracement|pullback|retrace)\w*\b",
        r"\b(retracement|pullback|retrace\w*)\s+(is|was)\s+(too\s+)?(shallow|deep)\b",
    ],
    "strong": [
        r"\bstrong(ly)?\s+(clos\w+|candle|body|move|expansion|reaction|displacement|"
        r"bullish|bearish|bias)\b",
        r"\bclos(es|ed|ing)\s+strong\b",
        r"\bstrength\s+(of|in|behind)\b",
    ],
}

# ── polarity cues ─────────────────────────────────────────────────────────────
REJECT_CUES = [
    r"\btoo\s+(large|big|much|small|wide|deep)\b",
    r"\bnot\s+(a|an|really|very|likely|going|enough|the)\b",
    r"\bno\s+(displacement|aggression|fair\s+value\s+gap|expansion|wick|real)\b",
    r"\b(isn't|wasn't|doesn't|didn't|don't|wouldn't|won't|can't|couldn't)\b",
    r"\bnever\b", r"\black\s+of\b", r"\bfail(s|ed|ing|ure)?\b",
    r"\binstead\s+of\b", r"\brather\s+than\b", r"\bavoid\b",
    r"\bunlikely\b", r"\bnot\s+likely\b", r"\bstay\s+(away|out)\b",
    r"\bwe\s+don't\s+want\b", r"\bi\s+don't\s+want\b",
]
ACCEPT_CUES = [
    r"\b(nice|beautiful|textbook|perfect|clean|ideal|great|good)\b",
    r"\b(we|you)\s+(have|get|got)\s+(a\s+)?(nice\s+)?(displacement|expansion|aggressive)\b",
    r"\byou\s+can\s+see\s+(we|price|this|that)\b",
    r"\bthat\s+is\s+(displacement|expansion|aggressive|a\s+small\s+wick)\b",
    r"\bthis\s+is\s+(displacement|expansion|aggressive)\b",
    r"\bexactly\s+what\b", r"\bwhat\s+(i|we)\s+want\s+to\s+see\b",
    r"\bqualifies\b", r"\bsupports?\s+expansion\b",
]
# Chart deixis: the author is pointing at a specific candle rather than lecturing.
DEIXIS_CUES = [
    r"\bthis\s+(candle|wick|run|move|leg|high|low|one)\b",
    r"\b(right\s+)?here\b", r"\bthere\s+you\s+go\b",
    r"\byou\s+can\s+see\b", r"\bwe\s+can\s+see\b",
    r"\bso\s+here\s+we\s+(are|have)\b",
]
# Judgement verbs: the author is *adjudicating*, not defining.
JUDGE_CUES = [
    r"\bwould\s+(form|be|make|have)\b", r"\bis\s+this\b", r"\bwas\s+this\b",
    r"\bqualif\w+\b", r"\bcounts?\s+as\b", r"\benough\b",
    r"\bi'?d?\s+want\s+to\s+see\b", r"\bi'?m\s+(not\s+)?(really\s+)?expecting\b",
    r"\bmy\s+expectations?\b", r"\bwe\s+want\s+to\s+focus\s+on\b",
    r"\bbetter\s+(to|than)\b", r"\bprefer\w*\b",
]

_C = lambda pats: [re.compile(p, re.I) for p in pats]  # noqa: E731
RX_TERMS = {k: _C(v) for k, v in TERM_PATTERNS.items()}
RX_REJECT, RX_ACCEPT = _C(REJECT_CUES), _C(ACCEPT_CUES)
RX_DEIXIS, RX_JUDGE = _C(DEIXIS_CUES), _C(JUDGE_CUES)


# ── transcript loading ────────────────────────────────────────────────────────
@dataclass
class Transcript:
    video_id: str
    title: str
    source: str
    playlists: str
    body: str

    @property
    def asr(self) -> bool:
        return self.source.lower().startswith("whisper")


def load_transcripts() -> dict[str, Transcript]:
    out: dict[str, Transcript] = {}
    for p in sorted(TRANSCRIPTS.glob("*.txt")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        head, _, body = raw.partition(SEP)
        meta = {}
        for line in head.splitlines():
            if line.startswith("# "):
                meta["title"] = line[2:].strip()
            elif ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
        vid = meta.get("video_id") or p.stem
        out[vid] = Transcript(
            video_id=vid,
            title=meta.get("title", ""),
            source=meta.get("transcript_source", "unknown"),
            playlists=meta.get("playlists", ""),
            body=(body or raw).strip(),
        )
    return out


# ── hit extraction ────────────────────────────────────────────────────────────
@dataclass
class Hit:
    video_id: str
    title: str
    term: str
    matched: str
    context: str
    label_auto: str
    score: int
    asr: bool
    cues: dict = field(default_factory=dict)


def _word_window(words: list[str], wi: int, span: int) -> str:
    return " ".join(words[max(0, wi - span): wi + span + 1])


def _any(rxs, text: str) -> list[str]:
    return [rx.pattern for rx in rxs if rx.search(text)]


def extract_hits(t: Transcript) -> list[Hit]:
    body = re.sub(r"\s+", " ", t.body)
    words = body.split(" ")
    # character offset -> word index
    offs, c = [], 0
    for w in words:
        offs.append(c)
        c += len(w) + 1

    def widx(char_pos: int) -> int:
        lo, hi = 0, len(offs) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if offs[mid] <= char_pos:
                lo = mid
            else:
                hi = mid - 1
        return lo

    hits: list[Hit] = []
    seen: set[tuple[str, int]] = set()
    for term, rxs in RX_TERMS.items():
        for rx in rxs:
            for m in rx.finditer(body):
                wi = widx(m.start())
                key = (term, wi // 6)          # collapse near-duplicate hits
                if key in seen:
                    continue
                seen.add(key)
                ctx = _word_window(words, wi, WINDOW_WORDS)
                pol = _word_window(words, wi, POLARITY_WORDS)
                rej, acc = _any(RX_REJECT, pol), _any(RX_ACCEPT, pol)
                dei, jud = _any(RX_DEIXIS, pol), _any(RX_JUDGE, pol)
                if rej and not acc:
                    label = "REJECT"
                elif acc and not rej:
                    label = "ACCEPT"
                elif acc and rej:
                    label = "MIXED"
                else:
                    label = "UNLABELLED"
                score = (2 * bool(dei) + 3 * bool(jud)
                         + 2 * bool(rej or acc) + (2 if term == "wick_size" else 0))
                hits.append(Hit(
                    video_id=t.video_id, title=t.title, term=term,
                    matched=m.group(0), context=ctx, label_auto=label,
                    score=score, asr=t.asr,
                    cues={"reject": rej, "accept": acc,
                          "deixis": bool(dei), "judge": bool(jud)}))
    return hits


# ── the hand review ───────────────────────────────────────────────────────────
# Everything below this line was produced by READING the top-scoring candidates,
# not by the regex. `probe` is a verbatim substring used to locate the call in
# the transcript (the script asserts it is present); `quote` is the <=15-word
# citable extract; `label` is the adjudicated verdict; `basis` names the
# mechanical quantity the call is actually about, which is what makes it usable
# in Part B (fit_thresholds.py).
#
# A call is only curated if BOTH hold:
#   (a) the author states a verdict about a specific object on the chart, and
#   (b) the verdict is about one of the five blocked terms.
# Generic definitional statements ("displacement is an aggressive move") are NOT
# curated -- they are already in concepts/, and they carry no label.
BASIS_GLOSSARY: dict[str, str] = {
    "opposing_run_definition":
        "open -> extreme AGAINST the intended direction. The corpus's own name for "
        "the numerator of every wick call; not high-minus-low, not both wicks.",
    "wick_vs_body":
        "opposing run / abs(close - open). Crossover 1.0 = the reversal-vs-expansion "
        "classification anchor.",
    "wick_share_of_range":
        "opposing run / (high - low). The denominator he names out loud "
        "('a small wick relative to the daily range').",
    "eq_half_of_range":
        "does the following retracement hold above 0.5 of the reference candle's "
        "range. Stated outright to BE the wick-size measure.",
    "half_of_wick":
        "does price respect 0.5 of the WICK (extreme -> body edge). The large-wick "
        "branch of the same rule.",
    "time_share_to_extreme":
        "elapsed fraction of the candle's period at which its extreme printed. "
        "Requires M1 data; 'almost half the time' is an attested reject.",
    "retracement_depth":
        "counter-trend pullback / impulse leg. The 'shallow' of expansion legs, a "
        "different object from the wick.",
    "leg_range_per_bar":
        "range covered per candle by a leg — 'fast and large range'.",
    "leg_one_sidedness":
        "share of candles in a leg closing in the leg's direction.",
    "displacement_window":
        "RESUME finding #7: after a swing breaks, compare N-candle window range and "
        "distance beyond the level against a non-displacing instance.",
    "fvg_present":
        "does the impulse leave a three-bar fair value gap. The one fully mechanical "
        "displacement proxy in the corpus.",
    "close_beyond_level":
        "does the candle CLOSE past the reference level rather than wick through it.",
    "close_position_in_range":
        "(close - low) / (high - low). 'Closes in the high or the low', 'lopsided'.",
    "synonymy":
        "not a measurement — evidence that two blocked terms are one term.",
}

CURATION: list[dict] = [
    # =====================================================================
    # WICK SIZE — the family with the most narrated verdicts, and the one
    # that turns out to carry an actual number.
    # =====================================================================
    # -- the definition of the numerator (what "the wick" is) --------------
    dict(video_id="SlWxhzhLo3A", term="wick_size", label="ANCHOR", voice="ttrades",
         probe="when I say opposing run, I mean from the opening price to that high",
         quote="when I say opposing run, I mean from the opening price to that high",
         basis="opposing_run_definition",
         note="FIXES THE NUMERATOR. The wick that matters is ONE-SIDED and directional: "
              "open -> extreme against the intended direction. Not high-minus-low, not "
              "the sum of both wicks. Every other call below measures this quantity."),
    dict(video_id="SlWxhzhLo3A", term="wick_size", label="ANCHOR", voice="ttrades",
         probe="it has a small wick on both sides and a large body",
         quote="it has a small wick on both sides and a large body",
         basis="wick_vs_body",
         note="The expansion-candle shape, stated for both sides. Paired with the "
              "reversal-candle anchors below this gives the wick:body = 1.0 crossover."),
    dict(video_id="ecTRHQrbYzI", term="wick_size", label="ANCHOR", voice="ttrades",
         probe="A reversal candle has a large wick and a small body.",
         quote="A reversal candle has a large wick and a small body.",
         basis="wick_vs_body",
         note="The hard anchor named in RESUME finding #5. Classification is wick vs "
              "body -- ratio 1.0 -- equivalently opposing-wick/range = 0.5 for a "
              "candle whose other wick is negligible."),
    dict(video_id="TND1aTpnq5c", term="wick_size", label="ANCHOR", voice="ttrades",
         probe="the wick is larger than the body",
         quote="the wick is larger than the body",
         basis="wick_vs_body",
         note="Independent restatement in a different video. Two independent sources "
              "is what makes wick:body = 1.0 safe to treat as corpus-attested rather "
              "than a single loose phrasing."),
    dict(video_id="Kf4c41_qO1s", term="wick_size", label="ACCEPT", voice="ttrades",
         probe="Candles that support expansion will have a small wick and a large body",
         quote="Candles that support expansion will have a small wick and a large body",
         basis="wick_vs_body",
         note="States the expansion side as the exact mirror of the reversal side, "
              "which is why 1.0 is the crossover and anything stricter is convention."),

    # -- THE NUMBER: equilibrium / 0.5 is stated to BE the wick-size measure
    dict(video_id="3eVxTV_7L2U", term="wick_size", label="ANCHOR", voice="guest",
         probe="It is a mechanical way to measure wick size.",
         quote="It is a mechanical way to measure wick size.",
         basis="eq_half_of_range",
         note="THE HEADLINE FINDING OF THIS WORKSTREAM. Asked why he marks equilibrium "
              "of the previous candle's range, the answer is that the EQ *is* the wick-"
              "size measure. That converts 'small wick' into a number: opposing run "
              "must not exceed 50% of the reference range. RESUME finding #5 said no "
              "number is stated for wick size -- strictly true for a wick:body ratio, "
              "but the 0.5-of-range formulation was hiding in plain sight under the "
              "word 'equilibrium'. Guest video (GXT), but see the TTrades-voice "
              "corroborations immediately below."),
    dict(video_id="3eVxTV_7L2U", term="wick_size", label="ANCHOR", voice="guest",
         probe="wanting to see the upper half of that range support price higher",
         quote="wanting to see the upper half of that range support price higher",
         basis="eq_half_of_range",
         note="The operational form of the same rule: the retracement low of the next "
              "candle must hold above the 50% of the reference candle's range."),
    dict(video_id="Te9jUijPXZo", term="wick_size", label="ANCHOR", voice="ttrades",
         probe="mark out the upper half of the candle for a bullish scenario",
         quote="mark out the upper half of the candle for a bullish scenario",
         basis="eq_half_of_range",
         note="TTrades' OWN VOICE stating the same 0.5 construction, and explicitly "
              "as the place 'price to form its upper or lower wick'. This is what "
              "promotes the 0.5 rule from guest material to channel method."),
    dict(video_id="J_EeS2_2CAM", term="wick_size", label="ANCHOR", voice="guest",
         probe="mechanically uh measures wick size that would support expansion",
         quote="mechanically uh measures wick size that would support expansion",
         basis="eq_half_of_range",
         note="Third independent statement of the identity, and it attributes the rule "
              "to TTrades ('This is also in a T trades video'). Also flags the residual "
              "ambiguity honestly: 'the upper half of this candle's range... or this "
              "wick range' -- two denominators, which Part B measures separately."),
    dict(video_id="J_EeS2_2CAM", term="wick_size", label="REJECT", voice="guest",
         probe="It would be creating a large wick which doesn't support expansion",
         quote="It would be creating a large wick which doesn't support expansion",
         basis="eq_half_of_range",
         note="The reject branch of the same filter: disrespecting the EQ IS what makes "
              "the wick large. Confirms the threshold is the EQ and not a separate test."),
    dict(video_id="J_EeS2_2CAM", term="wick_size", label="REJECT", voice="guest",
         probe="if the candle that you're trading within doesn't support expansion",
         quote="if the candle that you're trading within doesn't support expansion",
         basis="eq_half_of_range",
         note="Narrated verdict on a specific candle ('This candle has a very large "
              "wick... I can't mechanically trade this') with the stated consequence: "
              "skip to the next timeframe open rather than trade it."),
    dict(video_id="LKNQDAdId4s", term="wick_size", label="ANCHOR", voice="ttrades",
         probe="I'd want to see if price respects .5 of this Wick",
         quote="I'd want to see if price respects .5 of this Wick",
         basis="half_of_wick",
         note="The OTHER 0.5: half of the WICK rather than half of the candle range. "
              "Corpus uses both without distinguishing them by name (the corpus's own "
              "`half-wick-respect` concept records the collision). Part B computes both."),
    dict(video_id="LKNQDAdId4s", term="wick_size", label="REJECT", voice="ttrades",
         probe="immediately just falls through 50% of that Wick",
         quote="immediately just falls through 50% of that Wick",
         basis="half_of_wick",
         note="The trigger for the rejection below. Note this is a DYNAMIC intra-candle "
              "test on lower-timeframe data, not a closed-candle ratio -- the label "
              "arrives before the candle closes."),
    dict(video_id="LKNQDAdId4s", term="wick_size", label="REJECT", voice="ttrades",
         probe="as this would form too large of a wick for an expansion candle",
         quote="this would form too large of a wick for an expansion candle",
         basis="half_of_wick",
         note="The single clearest narrated rejection in the corpus, and its stated "
              "cause is the 50%-of-wick violation immediately preceding it."),
    dict(video_id="07lOxv39LdY", term="wick_size", label="ANCHOR", voice="guest",
         probe="it was such a large wick on that candle I would use 50%",
         quote="it was such a large wick on that candle I would use 50%",
         basis="half_of_wick",
         note="RESOLVES THE COLLISION between the two 0.5s: the default reference is "
              "50% of the CANDLE; the switch to 50% of the WICK is conditional on the "
              "wick being large. So they are one rule with a branch, not two rules."),
    dict(video_id="c7nk7ypJHN4", term="wick_size", label="ANCHOR", voice="ttrades",
         probe="you're going to want to see it respect 50% of this wick",
         quote="you're going to want to see it respect 50% of this wick",
         basis="half_of_wick",
         note="TTrades-voice restatement of the 50%-of-wick test, with a speed rider "
              "('and kind of do it rather quickly') that is not quantified."),

    # -- the TIME denominator, which M1 data makes measurable ---------------
    dict(video_id="SlWxhzhLo3A", term="wick_size", label="REJECT", voice="ttrades",
         probe="We use almost half the time and quite a bit of range on this move up",
         quote="We use almost half the time and quite a bit of range",
         basis="time_share_to_extreme",
         note="A NUMBER ON THE TIME AXIS: 'almost half the time' is already a reject. "
              "So the time-share threshold sits at or below 0.5. Measurable from M1 "
              "even though the ratio itself is never named."),
    dict(video_id="SlWxhzhLo3A", term="wick_size", label="REJECT", voice="ttrades",
         probe="It's going to use most of its time period and most of its range",
         quote="It's going to use most of its time period and most of its range",
         basis="time_share_to_extreme",
         note="The reversal-candle definition given on BOTH axes at once. 'Most' reads "
              "as > 0.5 on each, consistent with the EQ rule on the range axis."),
    dict(video_id="SlWxhzhLo3A", term="wick_size", label="ANCHOR", voice="ttrades",
         probe="Price generally forming its high or low early into the candle",
         quote="Price generally forming its high or low early into the candle",
         basis="time_share_to_extreme",
         note="The accept side on the time axis. 'Early' is unquantified; the only "
              "bound the corpus supplies is the 'almost half' rejection above."),
    dict(video_id="Kf4c41_qO1s", term="wick_size", label="ANCHOR", voice="ttrades",
         probe="we want to see price open, have a small wick formed early into the candle",
         quote="we want to see price open, have a small wick formed early into the candle",
         basis="time_share_to_extreme",
         note="Independent statement of the same time condition, in the video that also "
              "supplies the wick:body anchor. The two axes are always given together."),
    dict(video_id="-KKuZb5Z5aU", term="wick_size", label="ANCHOR", voice="ttrades",
         probe="we want this candle's high to form early into the candle",
         quote="we want this candle's high to form early into the candle",
         basis="time_share_to_extreme",
         note="Third independent statement. Note what follows it: 'But what confirms "
              "that?' -- the answer is a lower-timeframe CISD, not a ratio. The corpus "
              "prefers a confirmation event to a threshold, which is exactly why no "
              "threshold was ever stated."),
    dict(video_id="vn1RYjhJUnQ", term="wick_size", label="REJECT", voice="ttrades",
         probe="If it consolidates for half of the candle and then closes over",
         quote="If it consolidates for half of the candle and then closes over",
         basis="time_share_to_extreme",
         note="Applies the same half-the-time bound to CLOSURE QUALITY rather than wick "
              "size: half the candle spent consolidating downgrades the close to "
              "'usually just a consolidation'. This is the only place 'strong closure' "
              "gets any test at all."),

    # -- further narrated verdicts on specific candles ----------------------
    dict(video_id="uzPGXVYpVGc", term="wick_size", label="ACCEPT", voice="ttrades",
         probe="we have a small opposing run that allows this candle to have a small wick",
         quote="a small opposing run that allows this candle to have a small wick",
         basis="opposing_run_definition",
         note="ACCEPT stated causally: the small opposing run is what MAKES the wick "
              "small. Same object, two names."),
    dict(video_id="uzPGXVYpVGc", term="wick_size", label="REJECT", voice="ttrades",
         probe="I'm not really expecting price to just expand because it's made too large of a wick",
         quote="not really expecting price to just expand because it's made too large",
         basis="wick_share_of_range",
         note="Rejection on a 4-hour candle with the stated consequence: retarget the "
              "candle's OPEN instead of expansion."),
    dict(video_id="SlWxhzhLo3A", term="wick_size", label="ACCEPT", voice="ttrades",
         probe="Yes, we have a small wick relative to the daily range",
         quote="Yes, we have a small wick relative to the daily range",
         basis="wick_share_of_range",
         note="NAMES THE DENOMINATOR OUTRIGHT: the wick is judged 'relative to the daily "
              "range'. Combined with the EQ rule this is opposing_run / candle_range "
              "against a 0.5 cut."),
    dict(video_id="SlWxhzhLo3A", term="wick_size", label="REJECT", voice="ttrades",
         probe="We have a large wick. This doesn't support expansion.",
         quote="We have a large wick. This doesn't support expansion.",
         basis="wick_share_of_range",
         note="Clean per-candle rejection inside the corpus's dedicated wick-size video."),
    dict(video_id="YEkejZyV65A", term="wick_size", label="REJECT", voice="ttrades",
         probe="This is a candle with a large wick. It does not support expansion.",
         quote="This is a candle with a large wick. It does not support expansion.",
         basis="wick_share_of_range",
         note="Same verdict in a Short, on a 4-hour candle following a candle-2 closure."),
    dict(video_id="m4k_1pF5zFI", term="wick_size", label="REJECT", voice="ttrades",
         probe="this daily candle does not support expansion, right? We have a large wick",
         quote="this daily candle does not support expansion, right? We have a large wick",
         basis="wick_share_of_range",
         note="Daily-timeframe rejection. The label is applied identically on 1D, 4H and "
              "1H across the corpus, which is why Part B measures every timeframe."),
    dict(video_id="5UsKZ7pZqvY", term="wick_size", label="ANCHOR", voice="ttrades",
         probe="when we have a larger wick, my expectations is favoring back towards that daily open",
         quote="when we have a larger wick, my expectations is favoring back towards that daily",
         basis="wick_share_of_range",
         note="The large-wick branch's action, stated as a target change rather than a "
              "no-trade. Useful because it makes the label FALSIFIABLE: large-wick days "
              "should revert to the open more often than they expand."),
    dict(video_id="-KKuZb5Z5aU", term="wick_size", label="REJECT", voice="ttrades",
         probe="this is not a candle that I would be interested in trading",
         quote="this is not a candle that I would be interested in trading",
         basis="wick_share_of_range",
         note="Rejection inside the 'Easy Daily Bias - Mechanical Framework' video, "
              "i.e. even the video that advertises mechanism leaves this call to eye."),
    dict(video_id="WBwoiMDXT2c", term="wick_size", label="REJECT", voice="ttrades",
         probe="It has a large wick. I'm not really interested in trading that.",
         quote="It has a large wick. I'm not really interested in trading that.",
         basis="wick_share_of_range",
         note="Live-stream rejection on oil, unrehearsed -- useful because the teaching "
              "videos could be selecting clean examples and this one is not curated by him."),
    dict(video_id="yud7TpE2AMs", term="wick_size", label="ACCEPT", voice="ttrades",
         probe="that's enough of a wick. I don't want to see a bigger wick here",
         quote="that's enough of a wick. I don't want to see a bigger wick here",
         basis="wick_share_of_range",
         note="THE ONLY BOUNDARY CASE IN THE CORPUS -- an accept declared to be AT the "
              "limit ('Otherwise, it fails'), on a 4-hour candle described as 'barely "
              "making a wick'. A boundary label is worth more than a dozen clear-cut "
              "ones, but with no instrument or date spoken it still cannot be priced."),

    # =====================================================================
    # SHALLOW
    # =====================================================================
    dict(video_id="aQoMSAaIXsg", term="shallow", label="REJECT", voice="ttrades",
         probe="Is this a shallow run? No, this is a large opposing run.",
         quote="Is this a shallow run? No, this is a large opposing run.",
         basis="opposing_run_definition",
         note="Question, verdict, consequence -- the cleanest narrated adjudication in "
              "the corpus. Also binds 'shallow' and 'small wick' to ONE quantity, so "
              "the 23 shallow-blocked concepts inherit the wick threshold."),
    dict(video_id="SlWxhzhLo3A", term="shallow", label="ACCEPT", voice="ttrades",
         probe="Here we have a nice shallow run above the previous day high",
         quote="Here we have a nice shallow run above the previous day high",
         basis="opposing_run_definition",
         note="The matching ACCEPT for the same object type (a run above previous day "
              "high). Same video as the REJECT above, so the two are comparable."),
    dict(video_id="4Gm8p6O7Ebs", term="shallow", label="ANCHOR", voice="ttrades",
         probe="we have very shallow moves against the trend and that is the signature of expansion",
         quote="very shallow moves against the trend and that is the signature of expansion",
         basis="retracement_depth",
         note="'Shallow' applied to the COUNTER-TREND LEG inside an expansion -- a "
              "different object from the wick, on a different denominator (the impulse "
              "leg). Part B measures it separately rather than assuming one threshold."),
    dict(video_id="OzugLBi0PVQ", term="shallow", label="ANCHOR", voice="ttrades",
         probe="Expansion is aggressive, fast, and large range.",
         quote="Expansion is aggressive, fast, and large range.",
         basis="leg_range_per_bar",
         note="The contrastive definition -- retracements slow/shallow/small-range vs "
              "expansion aggressive/fast/large-range. Ties 'aggressive' to RANGE PER "
              "UNIT TIME, which is exactly the comparative procedure of RESUME #7."),
    dict(video_id="W7Fu3Rx5iMs", term="shallow", label="REJECT", voice="ttrades",
         probe="you don't get deep retracements there",
         quote="you don't get deep retracements there",
         basis="retracement_depth",
         note="Live-stream statement of the same rule for a 09:30-10:00 trend leg, "
              "and it is stated as the mechanical read ('Mechanically, after it hits a "
              "high, waiting for the continuation, that tells you it's not form[ing]')."),
    dict(video_id="0AYGNc9czYc", term="shallow", label="REJECT", voice="ttrades",
         probe="I would have wanted a shallow wick close below here",
         quote="I would have wanted a shallow wick close below here",
         basis="wick_share_of_range",
         note="Counterfactual rejection -- the setup worked anyway ('It still happened') "
              "but he grades it as not clean. Shows the label is about quality, not "
              "outcome, which matters when fitting to outcomes."),

    # =====================================================================
    # DISPLACEMENT / AGGRESSIVE  (one term, per b6yvRKf8haE below)
    # =====================================================================
    dict(video_id="b6yvRKf8haE", term="aggressive", label="ANCHOR", voice="ttrades",
         probe="had an aggressive move or displacement above",
         quote="had an aggressive move or displacement above",
         basis="synonymy",
         note="'aggressive move OR displacement' in apposition: the two separately-"
              "blocked terms are ONE term. Collapses 37 + 34 concepts onto a single "
              "threshold instead of two."),
    dict(video_id="1oco9lesido", term="displacement", label="ACCEPT", voice="ttrades",
         probe="when you break this short-term High you want to see an energetic move up",
         quote="when you break this short-term High you want to see an energetic move up",
         basis="displacement_window",
         note="Fixes the trigger event the measurement window is anchored to: a short-"
              "term high/low being broken, not an arbitrary bar."),
    dict(video_id="1oco9lesido", term="displacement", label="ANCHOR", voice="ttrades",
         probe="if you just take these four candles when we broke this High here",
         quote="if you just take these four candles when we broke this High here",
         basis="displacement_window",
         note="The window: FOUR candles from the break. Stated once, in one worked "
              "example, never as a parameter -- so Part B sweeps N."),
    dict(video_id="1oco9lesido", term="displacement", label="ANCHOR", voice="ttrades",
         probe="in the same amount of time right we have a larger range",
         quote="in the same amount of time right we have a larger range",
         basis="displacement_window",
         note="The comparison itself. RELATIVE, with no absolute threshold, so Part B "
              "implements it as stated and then reports what percentile the implied "
              "cut sits at so it can be made absolute."),
    dict(video_id="FdRKBTz0Fps", term="displacement", label="REJECT", voice="ttrades",
         probe="there's no displacement right there's no fair value gap or reach above energetically",
         quote="there's no displacement right there's no fair value gap or reach above",
         basis="fvg_present",
         note="Narrated REJECT whose stated ground is the ABSENCE OF AN FVG -- the one "
              "fully mechanical displacement proxy in the corpus."),
    dict(video_id="UmLWRlXd_V8", term="aggressive", label="REJECT", voice="mixed",
         probe="no fair value gaps no aggression so there's no reason to be bullish",
         quote="no fair value gaps no aggression so there's no reason to be bullish",
         basis="fvg_present",
         note="Second independent FVG-absence rejection, and it states the identity "
              "outright: no FVG == no aggression."),
    dict(video_id="_94CPMjWi9E", term="displacement", label="ANCHOR", voice="ttrades",
         probe="the easiest way to spot it is just looking for fair value gaps",
         quote="the easiest way to spot it is just looking for fair value gaps",
         basis="fvg_present",
         note="LATER canon: downgrades the FVG from requirement to detection aid. Both "
              "readings collapse to the same computable test, so the evolution does not "
              "change what to measure."),
    dict(video_id="sgAnVR6RSDg", term="displacement", label="ANCHOR", voice="ttrades",
         probe="now we get some displacement a close over this previous high",
         quote="now we get some displacement a close over this previous high",
         basis="close_beyond_level",
         note="His operational resolution every time he adjudicates on a chart: "
              "displacement == a CLOSE beyond the level. Note this makes a one-tick "
              "close qualify, which is precisely why a magnitude knob is still needed."),
    dict(video_id="5rbFskdmEmU", term="displacement", label="ANCHOR", voice="ttrades",
         probe="displacement is just large aggressive candles with closes in the high or the low",
         quote="displacement is just large aggressive candles with closes in the high or the low",
         basis="close_position_in_range",
         note="The closest thing to a wick rule for displacement: close AT the extreme. "
              "Computable as (close-low)/range near 1, and it is the SAME quantity as "
              "'small wick' viewed from the close side."),
    dict(video_id="4WCiIyCiBrQ", term="displacement", label="REJECT", voice="ttrades",
         probe="we can't get any displacement or a breakout of this range",
         quote="we can't get any displacement or a breakout of this range",
         basis="close_beyond_level",
         note="Rejection resolved purely as failure to close outside the range -- "
              "the consolidation branch of the same test."),
    dict(video_id="o0v4KQxZbpU", term="displacement", label="REJECT", voice="ttrades",
         probe="no displacement down yet displacement back up",
         quote="no displacement down yet displacement back up",
         basis="close_beyond_level",
         note="Two verdicts in one breath on consecutive legs, used to flip the target "
              "side. Shows the test is applied per-leg and continuously, not once."),
    dict(video_id="FXJBFbZQbck", term="displacement", label="ACCEPT", voice="ttrades",
         probe="here we get aggressive displacement below previous day low",
         quote="here we get aggressive displacement below previous day low",
         basis="close_beyond_level",
         note="ACCEPT on a daily candle closing below previous day low -- the same "
              "close-beyond-level test, positive side."),
    dict(video_id="mwmWNCTEYtY", term="aggressive", label="ACCEPT", voice="ttrades",
         probe="with this super aggressive close down here I'm not expecting a retracement right away",
         quote="with this super aggressive close down here I'm not expecting a retracement",
         basis="close_position_in_range",
         note="Grades aggression BY THE CLOSE and derives a timing consequence from it "
              "('I'll let a few candles form'). Falsifiable: strongly-closed candles "
              "should retrace later than weakly-closed ones."),
    dict(video_id="bMkRomKEunU", term="aggressive", label="REJECT", voice="ttrades",
         probe="this candle would have had it to trade pretty aggressively lower. It doesn't",
         quote="this candle would have had it to trade pretty aggressively lower. It doesn't",
         basis="close_position_in_range",
         note="Counterfactual rejection: what the candle would have needed to do to "
              "qualify, and the verdict that it did not. Resolves to candle shape "
              "('It forms a reversal candle')."),

    # =====================================================================
    # STRONG
    # =====================================================================
    dict(video_id="gjoRPszj-Qk", term="strong", label="ACCEPT", voice="guest",
         probe="this move right here is what I would consider strong displacement",
         quote="this move right here is what I would consider strong displacement",
         basis="close_position_in_range",
         note="The only place 'strong' is attached to a specific object and adjudicated. "
              "Guest (T Talks)."),
    dict(video_id="gjoRPszj-Qk", term="strong", label="ANCHOR", voice="guest",
         probe="You can see this is a pretty lopsided candle",
         quote="You can see this is a pretty lopsided candle",
         basis="close_position_in_range",
         note="The stated basis for 'strong': LOPSIDED, i.e. body dominates and the "
              "close is at the extreme. Note he accepts it despite 'a heavy wick' "
              "because there was a body close -- so 'strong' grades the CLOSE, not the "
              "wick, and is therefore NOT a synonym for 'small wick'."),
    dict(video_id="vn1RYjhJUnQ", term="strong", label="REJECT", voice="ttrades",
         probe="doesn't mean it's a good closure over",
         quote="doesn't mean it's a good closure over",
         basis="time_share_to_extreme",
         note="The only rejection of a CLOSURE on quality grounds, and its stated cause "
              "is time spent consolidating (see the paired entry above). This is all "
              "the corpus offers for 'strong closure' / fractal-model-c4."),
    dict(video_id="4Gm8p6O7Ebs", term="strong", label="ANCHOR", voice="ttrades",
         probe="expansion is when we have a one-sided trending move",
         quote="expansion is when we have a one-sided trending move",
         basis="leg_one_sidedness",
         note="Recorded so Part C can state what 'strong' INHERITS rather than inventing "
              "a test for it: one-sidedness of a leg plus a close near the extreme. "
              "'Strong' never gets its own threshold anywhere."),
]

def verify_curation(tx: dict[str, Transcript]) -> list[str]:
    """Reject a curated entry whose probe/quote is not verbatim, or >15 words."""
    errs: list[str] = []
    for e in CURATION:
        t = tx.get(e["video_id"])
        if t is None:
            errs.append(f"{e['video_id']}: no transcript")
            continue
        if t.asr:
            errs.append(f"{e['video_id']}: ASR transcript, excluded from curation")
        flat = re.sub(r"\s+", " ", t.body)
        for k in ("probe", "quote"):
            if re.sub(r"\s+", " ", e[k]) not in flat:
                errs.append(f"{e['video_id']} {k!r} not verbatim: {e[k][:60]!r}")
        if len(e["quote"].split()) > 15:
            errs.append(f"{e['video_id']} quote is {len(e['quote'].split())} words (>15)")
    return errs


# ── output ────────────────────────────────────────────────────────────────────
def main() -> None:
    tx = load_transcripts()
    asr_ids = sorted(v for v, t in tx.items() if t.asr)

    hits: list[Hit] = []
    for t in tx.values():
        hits.extend(extract_hits(t))
    hits.sort(key=lambda h: (-h.score, h.video_id))

    errs = verify_curation(tx)
    if errs:
        for e in errs:
            print("CURATION ERROR:", e)
        raise SystemExit("refusing to write: curation failed verification")

    by_term = Counter(h.term for h in hits)
    by_label = Counter(h.label_auto for h in hits)
    cur_by_term = Counter(e["term"] for e in CURATION)
    cur_by_label = Counter(e["label"] for e in CURATION)

    # precision of the automatic labeller, measured only where the hand review
    # gave a directional verdict (ACCEPT/REJECT) -- ANCHOR entries have no polarity.
    agree = tot = 0
    for e in CURATION:
        if e["label"] not in ("ACCEPT", "REJECT"):
            continue
        t = tx[e["video_id"]]
        flat = re.sub(r"\s+", " ", t.body)
        pos = flat.find(re.sub(r"\s+", " ", e["probe"]))
        words = flat.split(" ")
        wi = len(flat[:pos].split(" ")) - 1
        pol = _word_window(words, wi, POLARITY_WORDS)
        rej, acc = _any(RX_REJECT, pol), _any(RX_ACCEPT, pol)
        auto = ("REJECT" if rej and not acc else "ACCEPT" if acc and not rej
                else "MIXED" if acc and rej else "UNLABELLED")
        tot += 1
        agree += (auto == e["label"])

    payload = {
        "generated_from": str(TRANSCRIPTS),
        "transcripts_scanned": len(tx),
        "asr_transcripts": asr_ids,
        "candidate_count": len(hits),
        "candidates_by_term": dict(by_term),
        "candidates_by_auto_label": dict(by_label),
        "curated_count": len(CURATION),
        "curated_by_term": dict(cur_by_term),
        "curated_by_label": dict(cur_by_label),
        "auto_labeller_agreement_on_curated_directional":
            {"agree": agree, "of": tot},
        "curated": [dict(e, title=tx[e["video_id"]].title) for e in CURATION],
        "candidates": [asdict(h) for h in hits],
    }
    META.mkdir(exist_ok=True)
    (META / "qualifier_calls.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")

    # ---- markdown ----
    L: list[str] = []
    L.append("# Narrated qualifier calls — mined accept/reject labels\n")
    L.append("Generated by `python/mine_qualifiers.py`. **Do not hand-edit** — "
             "the curated table lives in the `CURATION` list inside that script, "
             "where every quote is checked verbatim against the transcript and "
             "capped at 15 words.\n")
    L.append(f"- transcripts scanned: **{len(tx)}**\n")
    L.append(f"- regex candidates: **{len(hits)}** "
             f"({', '.join(f'{k}={v}' for k, v in sorted(by_term.items()))})\n")
    L.append(f"- auto-label split: {dict(by_label)}\n")
    L.append(f"- **curated calls: {len(CURATION)}** "
             f"({', '.join(f'{k}={v}' for k, v in sorted(cur_by_label.items()))})\n")
    L.append(f"- ASR transcripts (jargon unreliable, excluded from curation): "
             f"{', '.join(asr_ids) or 'none'}\n")
    L.append(f"- automatic ACCEPT/REJECT labeller agreed with the hand review on "
             f"**{agree}/{tot}** directional calls — the regex is a *retrieval* "
             f"aid, not a labeller.\n")

    L.append("\n## What the labels mean\n")
    L.append("| label | meaning |\n|---|---|\n"
             "| `ACCEPT` | author points at a specific object and rules it *does* qualify |\n"
             "| `REJECT` | author points at a specific object and rules it does *not* qualify |\n"
             "| `ANCHOR` | not a per-object verdict but a stated comparative/definitional "
             "rule that pins a computable quantity (e.g. wick vs body) |\n")

    L.append("\n## The mechanical quantities the calls resolve to\n")
    L.append("This is the actual product of Part A. The calls do not price a "
             "threshold, but they do say *which number to compute* — and several "
             "say it in the author's own words.\n")
    L.append("\n| basis | calls | what it measures |\n|---|--:|---|\n")
    for b, desc in BASIS_GLOSSARY.items():
        n = sum(1 for e in CURATION if e["basis"] == b)
        L.append(f"| `{b}` | {n} | {desc} |\n")

    L.append("\n## Curated calls\n")
    for term in ("wick_size", "shallow", "displacement", "aggressive", "strong"):
        rows = [e for e in CURATION if e["term"] == term]
        if not rows:
            continue
        n_v = Counter(e["voice"] for e in rows)
        L.append(f"\n### {term} — {len(rows)} calls "
                 f"({', '.join(f'{k}={v}' for k, v in sorted(n_v.items()))})\n")
        for e in rows:
            t = tx[e["video_id"]]
            L.append(f"\n**{e['label']}** · `{e['video_id']}` · *{t.title}* · "
                     f"voice `{e['voice']}` · basis `{e['basis']}`\n\n")
            L.append(f"> {e['quote']}\n\n")
            L.append(f"{e['note']}\n")

    L.append("\n## Why the curated set is small\n")
    L.append(
        "The regex surfaces hundreds of hits but almost all of them are the author "
        "*using* the word, not *adjudicating* with it. A usable label needs the "
        "author to look at one object and return a verdict, and that is rare: the "
        "corpus teaches by definition and demonstration, not by labelled examples. "
        f"{len(CURATION)} genuinely-labelled calls is the honest yield. None of them "
        "can be tied to a datable bar (there is no chart in a transcript and no "
        "instrument or date is spoken), so they constrain **which quantity** to "
        "measure, not **what value** it takes. That distinction drives everything "
        "in `meta/threshold_fits.md`.\n")

    L.append("\n## Top regex candidates (unreviewed, ranked by narration score)\n")
    L.append("Score = deixis(2) + judgement verb(3) + polarity cue(2) + wick bonus(2). "
             "Shown for audit: this is what the hand review read.\n")
    L.append("\n| score | term | auto | video | matched | context |\n|--:|---|---|---|---|---|\n")
    for h in hits[:40]:
        ctx = h.context.replace("|", "/")
        ctx = (ctx[:220] + "…") if len(ctx) > 220 else ctx
        L.append(f"| {h.score} | {h.term} | {h.label_auto} | `{h.video_id}` | "
                 f"{h.matched} | …{ctx}… |\n")

    (META / "qualifier_calls.md").write_text("".join(L), encoding="utf-8")

    print(f"transcripts        : {len(tx)}")
    print(f"regex candidates   : {len(hits)}  {dict(by_term)}")
    print(f"auto labels        : {dict(by_label)}")
    print(f"curated calls      : {len(CURATION)}  {dict(cur_by_label)}")
    print(f"auto vs hand       : {agree}/{tot} directional")
    print(f"wrote {META/'qualifier_calls.md'}")
    print(f"wrote {META/'qualifier_calls.json'}")


if __name__ == "__main__":
    main()
