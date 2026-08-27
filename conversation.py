"""
conversation.py

Stores conversation context for the chatbot.
"""


class ConversationContext:

    def __init__(self):

        # Last detected course
        self.course_id = None

        # Last detected intent
        self.intent = None

        # Pending follow-up question/state.  This lets the bot continue
        # a clarification instead of treating the next short message
        # (for example "yes" or "python") as a brand-new question.
        self.pending = None


    # =====================================================
    # COURSE
    # =====================================================

    def set_course(self, course_id):

        if course_id:
            self.course_id = course_id


    def get_course(self):

        return self.course_id


    # =====================================================
    # INTENT
    # =====================================================

    def set_intent(self, intent):

        if intent:
            self.intent = intent


    def get_intent(self):

        return self.intent


    # =====================================================
    # PENDING FOLLOW-UP
    # =====================================================

    def set_pending(self, pending):
        self.pending = pending if pending else None


    def get_pending(self):
        return self.pending


    def clear_pending(self):
        self.pending = None


    # =====================================================
    # CLEAR
    # =====================================================

    def clear(self):

        self.course_id = None
        self.intent = None