# transformed 패키지 - 문제 변형 관련 기능
try:
    from .transform_multiple_choice import MultipleChoiceTransformer
    from .load_transformed_questions import load_transformed_questions
    from .create_transformed_exam import create_transformed_exam
    __all__ = [
        'MultipleChoiceTransformer',
        'load_transformed_questions',
        'create_transformed_exam'
    ]
except ImportError:
    MultipleChoiceTransformer = None
    load_transformed_questions = None
    create_transformed_exam = None
    __all__ = []

try:
    from .multi_essay_answer import generate_essay_answers
    if 'generate_essay_answers' not in __all__:
        __all__.append('generate_essay_answers')
except ImportError:
    generate_essay_answers = None


