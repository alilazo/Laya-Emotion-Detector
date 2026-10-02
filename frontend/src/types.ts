export type Emotion = "anxiety" | "sadness" | "fear";
export type Scores = Record<Emotion, number>;
export type Mode = "final" | "peak" | "average";
export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string | null;
  thinking_ms?: number | null;
  response_ms?: number | null;
  emotion_status: "pending" | "ready" | "unavailable" | "not_applicable";
  created_at: string;
};
export type Chat = {
  id: string;
  title: string;
  source: string;
  created_at: string;
  updated_at: string;
  current_anxiety: number;
  current_sadness: number;
  current_fear: number;
  emotion_message_count: number;
  messages?: Message[];
};
export type Node = {
  chatId: string;
  title: string;
  source: string;
  createdAt: string;
  messageCount: number;
  values: Scores;
  position: Scores;
  overallIntensity: number;
  dominantEmotion: Emotion | "neutral";
  mixed: boolean;
  neutral: boolean;
};
export type Analytics = {
  summary: {
    chatCount: number;
    averageAnxiety: number;
    averageSadness: number;
    averageFear: number;
    highAnxietyChats: number;
    highSadnessChats: number;
    highFearChats: number;
    mixedChats: number;
  };
  chats: Node[];
  totalInDateRange: number;
};
export type TimelinePoint = {
  sequence: number;
  messageId: string;
  createdAt: string;
  instant: Scores;
  gauge: Scores;
};
export type ChatEmotion = {
  summary: Record<Mode, Scores> | null;
  timeline: TimelinePoint[];
};
export const EMOTIONS: Emotion[] = ["anxiety", "sadness", "fear"];
export const LABELS: Record<Emotion, string> = {
  anxiety: "Anxiety",
  sadness: "Sadness",
  fear: "Scared",
};
