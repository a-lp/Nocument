from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace

from .template import DocumentTemplate, DocumentTemplateSummary


class RepositoryError(Exception):
    """The database is not reachable or refused the operation."""


@dataclass
class TemplateFilter:
    """
    Search criteria of the templates, combined together: text is looked for in the name and in the description (case
    insensitive); origins keeps only the templates with one of the given origins (all of them if empty).
    """
    text: str = ""
    origins: list[str] = field(default_factory=list)

    def matches(self, template: DocumentTemplate | DocumentTemplateSummary) -> bool:
        """True if the template matches the criteria."""
        text = self.text.casefold()
        return (
            (text in template.name.casefold() or text in template.description.casefold())
            and (not self.origins or template.origin in self.origins)
        )


class ITemplateRepository(ABC):
    """Access to the saved DocumentTemplates, independent of the database (repository pattern)."""

    @abstractmethod
    def get(self, template_id: str) -> DocumentTemplate | None:
        """Template with the given ID, with its Word file, or None if it does not exist."""

    @abstractmethod
    def list_summaries(self, criteria: TemplateFilter | None = None, skip: int = 0,
                       limit: int = 50) -> list[DocumentTemplateSummary]:
        """Summaries of the templates matching the criteria, from the most recent (updated_at)."""

    @abstractmethod
    def count(self, criteria: TemplateFilter | None = None) -> int:
        """Number of templates matching the criteria."""

    @abstractmethod
    def save(self, template: DocumentTemplate) -> None:
        """Saves the template, creating it or replacing the one with the same ID."""

    @abstractmethod
    def delete(self, template_id: str) -> bool:
        """Deletes the template; returns False if it did not exist."""


class InMemoryTemplateRepository(ITemplateRepository):
    """In-memory repository: for tests or to run the backend without a database (the data is lost on restart)."""

    def __init__(self):
        self._templates: dict[str, DocumentTemplate] = {}

    def get(self, template_id: str) -> DocumentTemplate | None:
        template = self._templates.get(template_id)
        return replace(template) if template is not None else None

    def list_summaries(self, criteria: TemplateFilter | None = None, skip: int = 0,
                       limit: int = 50) -> list[DocumentTemplateSummary]:
        return [template.summary() for template in self._matching(criteria)[skip:skip + limit]]

    def count(self, criteria: TemplateFilter | None = None) -> int:
        return len(self._matching(criteria))

    def save(self, template: DocumentTemplate) -> None:
        self._templates[template.id] = replace(template)

    def delete(self, template_id: str) -> bool:
        return self._templates.pop(template_id, None) is not None

    def _matching(self, criteria: TemplateFilter | None) -> list[DocumentTemplate]:
        """Templates matching the criteria, from the most recent."""
        criteria = criteria or TemplateFilter()
        templates = [template for template in self._templates.values() if criteria.matches(template)]
        return sorted(templates, key=lambda template: template.updated_at, reverse=True)
