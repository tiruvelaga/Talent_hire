try:
    from celery import shared_task
except ImportError:
    # Celery not installed - provide a dummy decorator
    def shared_task(func):
        return func

from .models import Candidate, Question, ExamAttempt, Answer, ExamSetting
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_exam_submission(candidate_id, question_ids, post_data):
    """
    Background task to calculate score and save exam results.
    """
    try:
        candidate = Candidate.objects.get(id=candidate_id)
        settings, _ = ExamSetting.objects.get_or_create(id=1)
        
        # Prevent double submission
        # (Assuming max_attempts is checked in view, but here we just process one)
        if ExamAttempt.objects.filter(candidate=candidate).count() >= settings.max_attempts:
            logger.warning(f"Candidate {candidate_id} has reached max attempts. Skipping.")
            return

        questions = {q.id: q for q in Question.objects.filter(id__in=question_ids)}
        score = 0
        answers_data = []

        for q_id in question_ids:
            question = questions.get(q_id)
            if not question:
                continue
            
            # Extract answer from post_data (which is a dict here)
            selected = post_data.get(f'q_{q_id}', '').strip().upper()
            is_correct = (selected == question.correct_answer)
            
            if is_correct:
                score += 1
                
            answers_data.append({
                'question': question,
                'selected_answer': selected if selected else None,
                'is_correct': is_correct,
            })

        total = settings.total_questions
        percentage = round((score / total) * 100, 2)
        status = "Selected" if percentage >= settings.min_selection_score else "Not Selected"

        # Save the attempt
        attempt = ExamAttempt.objects.create(
            candidate=candidate, 
            score=score, 
            total=total,
            percentage=percentage, 
            status=status,
        )

        # Save answers in bulk
        Answer.objects.bulk_create([
            Answer(
                attempt=attempt, 
                question=a['question'],
                selected_answer=a['selected_answer'], 
                is_correct=a['is_correct']
            )
            for a in answers_data
        ])
        
        logger.info(f"Successfully processed exam for candidate {candidate_id}. Score: {score}")

    except Exception as e:
        logger.error(f"Error processing exam for candidate {candidate_id}: {str(e)}")
        raise e
