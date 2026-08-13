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
    # CLEAR
    # =====================================================

    def clear(self):

        self.course_id = None
        self.intent = None