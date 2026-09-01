"""Contratos comuns para catálogos de perfis de teste."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

TestType = Literal["integracao", "e2e"]


@dataclass(frozen=True)
class StackTestProfile:
    """Descreve um adaptador de stack para integração ou E2E."""

    profile_id: str
    test_type: TestType
    stack: str
    framework: str
    source_suffixes: tuple[str, ...]
    marker_files: tuple[str, ...]
    test_file_pattern: str
    generator: str | None
    executor: str | None
    aliases: tuple[str, ...] = ()
    implemented: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class TestProfileRegistry:
    """Registro determinístico de perfis de um único nível de teste."""

    def __init__(
        self,
        test_type: TestType,
        profiles: tuple[StackTestProfile, ...] = (),
    ) -> None:
        self.test_type = test_type
        self._profiles: dict[str, StackTestProfile] = {}
        for profile in profiles:
            if profile.test_type != test_type:
                raise ValueError(
                    f"Perfil '{profile.profile_id}' pertence a {profile.test_type}, "
                    f"não a {test_type}."
                )
            if profile.profile_id in self._profiles:
                raise ValueError(f"Perfil duplicado: '{profile.profile_id}'.")
            self._profiles[profile.profile_id] = profile

    def __len__(self) -> int:
        return len(self._profiles)

    def get(self, profile_id: str) -> StackTestProfile | None:
        return self._profiles.get(profile_id)

    def list(self) -> list[dict]:
        return [profile.to_dict() for profile in self._profiles.values()]

    def values(self) -> tuple[StackTestProfile, ...]:
        return tuple(self._profiles.values())

    def resolve(self, value: str) -> tuple[StackTestProfile, ...]:
        """Resolve ID, stack ou framework sem escolher empates silenciosamente."""
        normalized = (value or "").strip().casefold().replace("_", "-")
        if not normalized:
            return ()
        matches = []
        for profile in self._profiles.values():
            aliases = {
                profile.profile_id.casefold().replace("_", "-"),
                profile.stack.casefold().replace("_", "-"),
                profile.framework.casefold().replace("_", "-"),
                *(alias.casefold().replace("_", "-") for alias in profile.aliases),
            }
            if normalized in aliases:
                matches.append(profile)
        return tuple(matches)
