"""Curated technology taxonomy and keyword matching for the Tech Stack Compatibility feature.

Two matchers exist per technology:
- ``strict``: for prose (job descriptions, repo descriptions). Aliases are matched
  case-insensitively as whole tokens; ambiguous spellings (``Go``, ``R``, ``C``, ``React``, ``Swift``,
  ``Spring``, ``Rails``) are matched case-sensitively, never next to ``-``, ``&`` or ``'``, and not
  before idiomatic follow-ups (``not_before``), so "good to go", "go-to", "Go above and beyond",
  "R&D" or "C-level" are not false positives.
- ``loose``: for identifiers (repo names, topics) after ``-``/``_`` are turned into spaces; every
  spelling is matched case-insensitively (``go-utils`` → Go, ``reactjs`` → React).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

Category = Literal["language", "framework", "database", "tool", "cloud"]

_PROSE_BEFORE = r"(?<![A-Za-z0-9+#.])"
_PROSE_AFTER = r"(?![A-Za-z0-9+#])"
_EXACT_BEFORE = r"(?<![A-Za-z0-9+#.&'\-])"
_EXACT_AFTER = r"(?![A-Za-z0-9+#&'\-])"


def _normalize(identifier: str) -> str:
    """Turn identifier separators into spaces (``spring-boot_demo`` → ``spring boot demo``)."""
    return re.sub(r"[-_]+", " ", identifier)


def _alternation(spellings: tuple[str, ...]) -> str:
    return "|".join(re.escape(s) for s in sorted(spellings, key=len, reverse=True))


@dataclass(frozen=True)
class Tech:
    """A canonical technology with its spellings and the GitHub languages that evidence it."""

    name: str
    category: Category
    aliases: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    exact: tuple[str, ...] = ()
    not_before: tuple[str, ...] = ()
    strict: re.Pattern[str] = field(init=False, repr=False, compare=False)
    loose: re.Pattern[str] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        parts = []
        if self.aliases:
            parts.append(f"{_PROSE_BEFORE}(?i:{_alternation(self.aliases)}){_PROSE_AFTER}")
        if self.exact:
            guard = rf"(?!\s+(?i:{_alternation(self.not_before)})\b)" if self.not_before else ""
            parts.append(f"{_EXACT_BEFORE}(?:{_alternation(self.exact)}){_EXACT_AFTER}{guard}")
        spellings = tuple({_normalize(s).lower() for s in (self.name, *self.aliases, *self.exact)})
        object.__setattr__(self, "strict", re.compile("|".join(parts)))
        object.__setattr__(
            self, "loose", re.compile(f"{_PROSE_BEFORE}(?:{_alternation(spellings)}){_PROSE_AFTER}", re.I)
        )

    def in_text(self, text: str) -> bool:
        """True if prose ``text`` mentions this technology."""
        return bool(self.strict.search(text))

    def in_identifier(self, identifier: str) -> bool:
        """True if a repo name or topic (e.g. ``my-react-app``) mentions this technology."""
        return bool(self.loose.search(_normalize(identifier)))


TECHNOLOGIES: tuple[Tech, ...] = (
    # Languages
    Tech("Python", "language", ("python", "python3"), ("Python",)),
    Tech("JavaScript", "language", ("javascript", "js", "es6", "ecmascript"), ("JavaScript",)),
    Tech("TypeScript", "language", ("typescript", "ts"), ("TypeScript",)),
    Tech("Java", "language", ("java", "j2ee", "java ee"), ("Java",)),
    Tech(
        "Go", "language", ("golang",), ("Go",), exact=("Go",),
        not_before=("above", "beyond", "the extra", "live", "to", "ahead", "out", "back",
                    "through", "get", "getter", "over", "into", "far", "further", "big"),
    ),
    Tech("Rust", "language", ("rust", "rustlang"), ("Rust",)),
    Tech("C++", "language", ("c++", "cpp"), ("C++",)),
    Tech("C#", "language", ("c#", "csharp", ".net", "dotnet", "asp.net"), ("C#",)),
    Tech("C", "language", (), ("C",), exact=("C",)),
    Tech("Ruby", "language", ("ruby",), ("Ruby",)),
    Tech("PHP", "language", ("php",), ("PHP",)),
    Tech("Swift", "language", ("swiftui",), ("Swift",), exact=("Swift",), not_before=("delivery", "response")),
    Tech("Kotlin", "language", ("kotlin",), ("Kotlin",)),
    Tech("Scala", "language", ("scala",), ("Scala",)),
    Tech("R", "language", ("rstats",), ("R",), exact=("R",)),
    Tech("Dart", "language", ("dart",), ("Dart",)),
    Tech("Objective-C", "language", ("objective-c", "objc"), ("Objective-C",)),
    Tech("HTML", "language", ("html", "html5"), ("HTML",)),
    Tech("CSS", "language", ("css", "css3", "scss", "sass"), ("CSS", "SCSS")),
    Tech("Shell", "language", ("shell", "bash", "shell scripting", "zsh"), ("Shell",)),
    Tech("SQL", "language", ("sql", "t-sql", "pl/sql"), ("TSQL", "PLSQL", "PLpgSQL")),
    # Frameworks & libraries
    Tech(
        "React", "framework", ("react.js", "reactjs", "react native"), ("JavaScript", "TypeScript"),
        exact=("React",), not_before=("quickly", "fast", "to", "promptly", "calmly", "well"),
    ),
    Tech("Vue", "framework", ("vue", "vue.js", "vuejs"), ("Vue", "JavaScript", "TypeScript")),
    Tech("Angular", "framework", ("angular", "angularjs"), ("TypeScript", "JavaScript")),
    Tech("Next.js", "framework", ("next.js", "nextjs"), ("JavaScript", "TypeScript")),
    Tech("Svelte", "framework", ("svelte", "sveltekit"), ("Svelte",)),
    Tech("Node.js", "framework", ("node.js", "nodejs", "node"), ("JavaScript", "TypeScript")),
    Tech("Express", "framework", ("express.js", "expressjs"), ("JavaScript", "TypeScript")),
    Tech("Django", "framework", ("django",), ("Python",)),
    Tech("Flask", "framework", ("flask",), ("Python",)),
    Tech("FastAPI", "framework", ("fastapi",), ("Python",)),
    Tech(
        "Spring", "framework", ("spring boot", "springboot", "spring framework"), ("Java", "Kotlin"),
        exact=("Spring",), not_before=("semester", "term", "break", "internship", "hiring", "intake", "season"),
    ),
    Tech("Rails", "framework", ("ruby on rails", "ror"), ("Ruby",), exact=("Rails",)),
    Tech("Laravel", "framework", ("laravel",), ("PHP",)),
    Tech("Flutter", "framework", ("flutter",), ("Dart",)),
    Tech("TensorFlow", "framework", ("tensorflow", "keras"), ()),
    Tech("PyTorch", "framework", ("pytorch", "torch"), ()),
    Tech("scikit-learn", "framework", ("scikit-learn", "sklearn", "scikit learn"), ()),
    Tech("Pandas", "framework", ("pandas",), ()),
    Tech("NumPy", "framework", ("numpy",), ()),
    Tech("Tailwind CSS", "framework", ("tailwind", "tailwindcss", "tailwind css"), ()),
    Tech("GraphQL", "framework", ("graphql",), ()),
    # Databases
    Tech("PostgreSQL", "database", ("postgresql", "postgres", "psql"), ("PLpgSQL",)),
    Tech("MySQL", "database", ("mysql", "mariadb"), ()),
    Tech("SQLite", "database", ("sqlite", "sqlite3"), ()),
    Tech("MongoDB", "database", ("mongodb", "mongo", "mongoose"), ()),
    Tech("Redis", "database", ("redis",), ()),
    Tech("Elasticsearch", "database", ("elasticsearch", "elastic search", "opensearch"), ()),
    # Tools
    Tech("Docker", "tool", ("docker", "dockerfile", "docker-compose", "containerization"), ("Dockerfile",)),
    Tech("Kubernetes", "tool", ("kubernetes", "k8s", "helm"), ()),
    Tech("Terraform", "tool", ("terraform",), ("HCL",)),
    Tech("Ansible", "tool", ("ansible",), ()),
    Tech("Kafka", "tool", ("kafka", "apache kafka"), ()),
    Tech("GitHub Actions", "tool", ("github actions", "github-actions"), ()),
    Tech("Jenkins", "tool", ("jenkins",), ()),
    Tech("Jupyter Notebook", "tool", ("jupyter", "jupyter notebook", "ipynb"), ("Jupyter Notebook",)),
    Tech("Linux", "tool", ("linux", "ubuntu"), ()),
    # Cloud
    Tech("AWS", "cloud", ("aws", "amazon web services", "lambda", "ec2"), ()),
    Tech("GCP", "cloud", ("gcp", "google cloud", "google cloud platform"), ()),
    Tech("Azure", "cloud", ("azure", "microsoft azure"), ()),
    Tech("Firebase", "cloud", ("firebase",), ()),
)

TECH_BY_NAME: dict[str, Tech] = {t.name: t for t in TECHNOLOGIES}


def extract_technologies(text: str) -> list[Tech]:
    """Return the distinct technologies mentioned in prose ``text``, in order of first mention."""
    positions: list[tuple[int, Tech]] = []
    for tech in TECHNOLOGIES:
        found = tech.strict.search(text)
        if found:
            positions.append((found.start(), tech))
    return [tech for _, tech in sorted(positions, key=lambda p: p[0])]
