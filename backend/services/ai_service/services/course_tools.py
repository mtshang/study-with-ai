from ..clients.learning import read_current_course

class CourseReadTools:
    """Bind verified identity outside the model; no user ID argument exposed to a model."""

    def __init__(self, cookie, principal):
        self._cookie = cookie
        self._principal = principal

    def get_current_course(self, course_id):
        return read_current_course(self._cookie, self._principal.id, course_id)
