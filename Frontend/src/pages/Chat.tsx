import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Plus, LogOut, Sparkles, User, Bot, Home, Trash2, X } from "lucide-react";
import logo from "@/assets/logo.png";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
}

interface SurveyData {
  activity: string;
  competitionType: string;
  projectName: string;
  specialConditions: string;
  workScope: string;
  projectDuration: string;
}

const Chat = () => {
  const navigate = useNavigate();

  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [currentUserEmail, setCurrentUserEmail] = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [showSurvey, setShowSurvey] = useState(false);
  const [surveyData, setSurveyData] = useState<SurveyData>({
    activity: "",
    competitionType: "",
    projectName: "",
    specialConditions: "",
    workScope: "",
    projectDuration: "",
  });

  const activityOptions = ["تصميم", "تطوير", "استشارات", "تسويق", "إدارة مشاريع", "توريد"];

  const competitionTypeOptions = [
    "منافسة عامة",
    "منافسة محدودة",
    "منافسة على مرحلتين",
    "اتفاقية إطار",
    "شراء مباشر / تعميد",
  ];

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  const getConversationsKey = (email: string) => `ic_conversations_${email}`;

  const loadUserConversations = (email: string) => {
    const key = getConversationsKey(email);
    const saved = localStorage.getItem(key);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // ✅ تحويل التواريخ من string إلى Date
        const normalized = parsed.map((conv: any) => ({
          ...conv,
          createdAt: new Date(conv.createdAt),
          messages: conv.messages.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }))
        }));
        setConversations(normalized);
      } catch (e) {
        console.error("Error loading conversations:", e);
        setConversations([]);
      }
    } else {
      setConversations([]);
    }
  };

  const saveUserConversations = (email: string, convs: Conversation[]) => {
    const key = getConversationsKey(email);
    localStorage.setItem(key, JSON.stringify(convs));
  };

  useEffect(() => {
    const user = localStorage.getItem("ic_user");
    if (!user) {
      navigate("/auth");
      return;
    }
    const userData = JSON.parse(user);
    setCurrentUserEmail(userData.email);
    setIsAuthenticated(true);
    loadUserConversations(userData.email);
  }, [navigate]);

  const activeConversation = conversations.find((c) => c.id === activeConversationId);
  const messages = activeConversation?.messages || [];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (currentUserEmail) saveUserConversations(currentUserEmail, conversations);
  }, [conversations, currentUserEmail]);

  // ✅ FIX: دالة محسّنة لعرض عنوان المحادثة
  const getConversationTitle = (conv: Conversation) => {
    // أولاً: نتحقق من الـ title المحفوظ
    if (conv.title && conv.title.trim() && conv.title !== "محادثة جديدة") {
      return conv.title;
    }

    // ثانياً: نبحث عن أول رسالة من المستخدم
    const firstUserMsg = conv.messages?.find((m) => m.role === "user");
    if (firstUserMsg?.content) {
      const content = firstUserMsg.content.trim();
      // نستخرج اسم المشروع من النص إذا كان موجود
      const projectNameMatch = content.match(/اسم المشروع:\s*(.+)/);
      if (projectNameMatch && projectNameMatch[1]) {
        const projectName = projectNameMatch[1].trim();
        return projectName.length > 40 
          ? projectName.slice(0, 40) + "..." 
          : projectName;
      }
      
      // لو مافي اسم مشروع، ناخذ أول سطر
      const firstLine = content.split('\n')[0].trim();
      return firstLine.length > 40 
        ? firstLine.slice(0, 40) + "..." 
        : firstLine;
    }

    // آخر حل: تاريخ الإنشاء
    return `محادثة ${new Date(conv.createdAt).toLocaleDateString('ar-SA')}`;
  };

  const handleSurveySubmit = async () => {
    if (!surveyData.projectName.trim()) return alert("يرجى إدخال اسم المشروع");
    if (!surveyData.activity) return alert("يرجى اختيار نشاط المنافسة");
    if (!surveyData.competitionType) return alert("يرجى اختيار نوع المنافسة");

    const userSummary = [
      "تم تزويد بيانات المشروع لتوليد العرض الفني:",
      `- نوع المنافسة: ${surveyData.competitionType}`,
      `- نشاط المنافسة: ${surveyData.activity}`,
      `- اسم المشروع: ${surveyData.projectName}`,
      `- الشروط الخاصة: ${surveyData.specialConditions || "لا يوجد"}`,
      `- نطاق العمل: ${surveyData.workScope || "غير محدد"}`,
      `- مدة المشروع: ${surveyData.projectDuration || "غير محددة"}`,
    ].join("\n");

    const newConversationId = Date.now().toString();

    const welcomeMessage: Message = {
      id: Date.now().toString(),
      content: userSummary,
      role: "user",
      timestamp: new Date(),
    };

    const pendingAiMessageId = (Date.now() + 1).toString();
    const pendingAiMessage: Message = {
      id: pendingAiMessageId,
      content: "جاري إنشاء العرض الفني...",
      role: "assistant",
      timestamp: new Date(),
    };

    // ✅ FIX: نحفظ اسم المشروع بشكل صحيح
    const newConversation: Conversation = {
      id: newConversationId,
      title: surveyData.projectName.trim(), // ✅ نحفظ الاسم مباشرة
      messages: [welcomeMessage, pendingAiMessage],
      createdAt: new Date(),
    };

    setConversations((prev) => [newConversation, ...prev]);
    setActiveConversationId(newConversationId);
    setIsTyping(true);
    setShowSurvey(false);

    try {
      const payload = {
        project_activity: surveyData.activity,
        competition_type: surveyData.competitionType,
        project_name: surveyData.projectName,
        special_conditions: surveyData.specialConditions || "",
        scope_of_work: surveyData.workScope || "",
        project_duration: surveyData.projectDuration || "",
      };

      const res = await fetch(`${API_BASE_URL}/api/generate-proposal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`API Error ${res.status}: ${text}`);
      }

      const data = await res.json();
      console.log("Compliance Score:", data?.compliance_score);
      const markdown = data?.markdown || "No content returned.";
      
      // ✅ إضافة نسبة الامتثال في النهاية مع مؤشر لوني
      let contentWithCompliance = markdown;
      if (data?.compliance_score !== null && data?.compliance_score !== undefined) {
        const complianceScore = Math.round(data.compliance_score);
        let statusText = "";
        let colorSymbol = "";
        
        if (complianceScore >= 70) {
          statusText = "متطابق بشكل عالي";
          colorSymbol = "🟢"; // أخضر
        } else if (complianceScore >= 40) {
          statusText = "متطابق بشكل متوسط";
          colorSymbol = "🟡"; // أصفر
        } else {
          statusText = "متطابق بشكل منخفض";
          colorSymbol = "🔴"; // أحمر
        }
        
        // عرض النسبة في النهاية مع مؤشر ملون
        const complianceSection = `
---

### درجة الامتثال
${colorSymbol} **${complianceScore}/100** - ${statusText}
`;

        contentWithCompliance = markdown + complianceSection;
      }

      setConversations((prev) =>
        prev.map((conv) => {
          if (conv.id !== newConversationId) return conv;

          return {
            ...conv,
            messages: conv.messages.map((m) =>
              m.id === pendingAiMessageId
                ? { ...m, content: contentWithCompliance }
                : m
            ),
          };
        })
      );
    } catch (err) {
      console.error(err);

      setConversations((prev) =>
        prev.map((conv) => {
          if (conv.id !== newConversationId) return conv;

          return {
            ...conv,
            messages: conv.messages.map((m) =>
              m.id === pendingAiMessageId
                ? {
                    ...m,
                    content:
                      "An error occurred while generating the technical proposal. Please ensure the API is running and the endpoint URL is correct.",
                  }
                : m
            ),
          };
        })
      );
    } finally {
      setIsTyping(false);
      setSurveyData({
        activity: "",
        competitionType: "",
        projectName: "",
        specialConditions: "",
        workScope: "",
        projectDuration: "",
      });
    }
  };

  const createNewConversation = () => setShowSurvey(true);

  const deleteConversation = (id: string) => {
    const updated = conversations.filter((c) => c.id !== id);
    setConversations(updated);
    if (activeConversationId === id) setActiveConversationId(null);
  };

  const handleSend = async () => {
    if (!input.trim() || !activeConversationId) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: "user",
      timestamp: new Date(),
    };

    setConversations((prev) =>
      prev.map((conv) => {
        if (conv.id === activeConversationId) {
          const updatedMessages = [...conv.messages, userMessage];
          const newTitle =
            conv.title === "محادثة جديدة"
              ? input.slice(0, 30) + (input.length > 30 ? "..." : "")
              : conv.title;
          return { ...conv, messages: updatedMessages, title: newTitle };
        }
        return conv;
      })
    );

    setInput("");
    setIsTyping(true);

    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "This is a demo reply. Connect the chat endpoint if you want real responses here.",
        role: "assistant",
        timestamp: new Date(),
      };

      setConversations((prev) =>
        prev.map((conv) => {
          if (conv.id === activeConversationId) {
            return { ...conv, messages: [...conv.messages, aiMessage] };
          }
          return conv;
        })
      );

      setIsTyping(false);
    }, 800);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("ic_user");
    navigate("/");
  };

  const userData = JSON.parse(
    localStorage.getItem("ic_user") || '{"name": "مستخدم", "email": "user@example.com"}'
  );

  if (!isAuthenticated) return null;

  return (
    <div className="h-screen flex bg-background" dir="rtl">
      {showSurvey && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div
            className="bg-card rounded-2xl shadow-2xl max-w-2xl w-full flex flex-col"
            style={{ maxHeight: "85vh" }}
          >
            <div className="flex items-center justify-between p-6 border-b border-border flex-shrink-0">
              <h2 className="text-2xl font-bold text-foreground">معلومات المشروع</h2>
              <button
                onClick={() => setShowSurvey(false)}
                className="p-2 hover:bg-muted rounded-lg transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="space-y-3">
                <Label className="text-lg font-semibold">
                  نوع المنافسة <span className="text-destructive">*</span>
                </Label>
                <RadioGroup
                  value={surveyData.competitionType}
                  onValueChange={(value) =>
                    setSurveyData((prev) => ({ ...prev, competitionType: value }))
                  }
                  className="grid grid-cols-2 gap-4"
                >
                  {competitionTypeOptions.map((t) => (
                    <div key={t} className="flex items-center gap-2 justify-end">
                      <label htmlFor={`ct-${t}`} className="text-sm font-medium cursor-pointer">
                        {t}
                      </label>
                      <RadioGroupItem value={t} id={`ct-${t}`} />
                    </div>
                  ))}
                </RadioGroup>
              </div>

              <div className="space-y-3">
                <Label className="text-lg font-semibold">
                  نشاط المنافسة <span className="text-destructive">*</span>
                </Label>
                <RadioGroup
                  value={surveyData.activity}
                  onValueChange={(value) => setSurveyData((prev) => ({ ...prev, activity: value }))}
                  className="grid grid-cols-3 gap-4"
                >
                  {activityOptions.map((activity) => (
                    <div key={activity} className="flex items-center gap-2 justify-end">
                      <label htmlFor={activity} className="text-sm font-medium cursor-pointer">
                        {activity}
                      </label>
                      <RadioGroupItem value={activity} id={activity} />
                    </div>
                  ))}
                </RadioGroup>
              </div>

              <div className="space-y-2">
                <Label htmlFor="projectName" className="text-lg font-semibold">
                  اسم المشروع <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="projectName"
                  placeholder="أدخل اسم المشروع"
                  value={surveyData.projectName}
                  onChange={(e) =>
                    setSurveyData((prev) => ({ ...prev, projectName: e.target.value }))
                  }
                  className="h-12"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="specialConditions" className="text-lg font-semibold">
                  الشروط الخاصة
                </Label>
                <Textarea
                  id="specialConditions"
                  placeholder="أدخل الشروط الخاصة بالمشروع..."
                  value={surveyData.specialConditions}
                  onChange={(e) =>
                    setSurveyData((prev) => ({ ...prev, specialConditions: e.target.value }))
                  }
                  className="min-h-24 resize-none"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="workScope" className="text-lg font-semibold">
                  نطاق العمل
                </Label>
                <Textarea
                  id="workScope"
                  placeholder="حدد نطاق العمل المطلوب..."
                  value={surveyData.workScope}
                  onChange={(e) => setSurveyData((prev) => ({ ...prev, workScope: e.target.value }))}
                  className="min-h-24 resize-none"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="projectDuration" className="text-lg font-semibold">
                  مدة المشروع
                </Label>
                <Input
                  id="projectDuration"
                  placeholder="مثال: 3 أشهر، 6 أسابيع..."
                  value={surveyData.projectDuration}
                  onChange={(e) =>
                    setSurveyData((prev) => ({ ...prev, projectDuration: e.target.value }))
                  }
                  className="h-12"
                />
              </div>
            </div>

            <div className="p-6 border-t border-border flex gap-3 flex-shrink-0">
              <Button onClick={() => setShowSurvey(false)} variant="outline" className="flex-1">
                إلغاء
              </Button>
              <Button onClick={handleSurveySubmit} variant="hero" className="flex-1">
                بدء المحادثة
              </Button>
            </div>
          </div>
        </div>
      )}

      <aside className="w-72 bg-sidebar flex flex-col border-l border-sidebar-border">
        <div className="p-6 border-b border-sidebar-border">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <img src={logo} alt="IC AI" className="h-10 w-auto" />
              <span className="text-lg font-bold text-sidebar-foreground">IC AI</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate("/")}
              className="text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent"
              title="العودة للرئيسية"
            >
              <Home className="h-5 w-5" />
            </Button>
          </div>

          <div className="bg-sidebar-accent rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center">
                <User className="h-5 w-5 text-secondary-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-sidebar-foreground truncate">
                  {userData.name}
                </p>
                <p className="text-xs text-sidebar-foreground/70 truncate">{userData.email}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="p-4">
          <Button
            onClick={() => setShowSurvey(true)}
            className="w-full justify-start gap-3 bg-secondary text-secondary-foreground hover:bg-secondary/90"
          >
            <Plus className="h-4 w-4" />
            محادثة جديدة
          </Button>
        </div>

        <ScrollArea className="flex-1 px-4">
          <div className="space-y-2 pb-4">
            {conversations.length > 0 ? (
              <>
                <div className="text-xs text-sidebar-foreground/50 px-2 py-2">المحادثات السابقة</div>
                {conversations.map((conv) => {
                  const displayTitle = getConversationTitle(conv);
                  return (
                    <div
                      key={conv.id}
                      className={`group flex items-center gap-2 w-full text-right p-3 rounded-lg text-sm transition-colors cursor-pointer ${
                        activeConversationId === conv.id
                          ? "bg-sidebar-primary text-sidebar-primary-foreground"
                          : "text-sidebar-foreground/80 hover:bg-sidebar-accent"
                      }`}
                      onClick={() => setActiveConversationId(conv.id)}
                      title={displayTitle}
                    >
                      <span className="flex-1 truncate">{displayTitle}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteConversation(conv.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/20 rounded transition-opacity"
                      >
                        <Trash2 className="h-3 w-3 text-destructive" />
                      </button>
                    </div>
                  );
                })}
              </>
            ) : (
              <div className="text-center py-8 text-sidebar-foreground/50 text-sm">
                لا توجد محادثات بعد
                <br />
                <span className="text-xs">اضغط "محادثة جديدة" للبدء</span>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="p-4 border-t border-sidebar-border space-y-2">
          <Button
            variant="ghost"
            onClick={handleLogout}
            className="w-full justify-start gap-3 text-sidebar-foreground/80 hover:text-destructive hover:bg-destructive/10"
          >
            <LogOut className="h-4 w-4" />
            تسجيل الخروج
          </Button>
        </div>
      </aside>

      <main className="flex-1 flex flex-col">
        <header className="h-16 border-b border-border flex items-center justify-between px-6 bg-card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-secondary/10 flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-secondary" />
            </div>
            <div>
              <h1 className="font-semibold text-foreground">IC AI Assistant</h1>
            </div>
          </div>
        </header>

        {activeConversationId ? (
          <>
            <ScrollArea className="flex-1 px-6 py-4">
              <div className="max-w-3xl mx-auto space-y-6">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-4 fade-in ${message.role === "user" ? "flex-row-reverse" : ""}`}
                  >
                    <div
                      className={`w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center ${
                        message.role === "user" ? "bg-secondary" : "bg-primary"
                      }`}
                    >
                      {message.role === "user" ? (
                        <User className="h-5 w-5 text-secondary-foreground" />
                      ) : (
                        <Bot className="h-5 w-5 text-primary-foreground" />
                      )}
                    </div>

                    <div
                      className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                        message.role === "user"
                          ? "bg-secondary text-secondary-foreground rounded-br-none"
                          : "bg-card border border-border rounded-bl-none"
                      }`}
                    >
                      {message.role === "assistant" ? (
                        <div
                          dir="rtl"
                          style={{ direction: "rtl", textAlign: "right" }}
                          className="prose prose-sm max-w-none text-right"
                        >
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              table: ({ node, ...props }) => (
                                <div className="overflow-x-auto my-5">
                                  <table
                                    {...props}
                                    dir="rtl"
                                    style={{ direction: "rtl" }}
                                    className="min-w-full border border-border text-sm text-right border-collapse"
                                  />
                                </div>
                              ),
                              thead: ({ node, ...props }) => (
                                <thead {...props} className="bg-muted" />
                              ),
                              th: ({ node, ...props }) => (
                                <th
                                  {...props}
                                  dir="rtl"
                                  style={{ textAlign: "right" }}
                                  className="border border-border px-3 py-2 font-semibold align-top text-right"
                                />
                              ),
                              td: ({ node, ...props }) => (
                                <td
                                  {...props}
                                  dir="rtl"
                                  style={{ textAlign: "right" }}
                                  className="border border-border px-3 py-2 align-top text-right"
                                />
                              ),
                              ul: ({ node, ...props }) => (
                                <ul {...props} className="list-disc pr-6" />
                              ),
                              ol: ({ node, ...props }) => (
                                <ol {...props} className="list-decimal pr-6" />
                              ),
                              li: ({ node, ...props }) => (
                                <li {...props} className="my-1" />
                              ),
                              code: ({ node, ...props }) => (
                                <code {...props} dir="ltr" style={{ direction: "ltr" }} />
                              ),
                              pre: ({ node, ...props }) => (
                                <pre {...props} dir="ltr" style={{ direction: "ltr" }} />
                              ),
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <p className="text-sm leading-relaxed whitespace-pre-line">{message.content}</p>
                      )}
                    </div>
                  </div>
                ))}

                {isTyping && (
                  <div className="flex gap-4 fade-in">
                    <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center">
                      <Bot className="h-5 w-5 text-primary-foreground" />
                    </div>
                    <div className="bg-card border border-border rounded-2xl rounded-bl-none px-5 py-3">
                      <div className="flex gap-1">
                        <span
                          className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                          style={{ animationDelay: "0ms" }}
                        />
                        <span
                          className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                          style={{ animationDelay: "150ms" }}
                        />
                        <span
                          className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                          style={{ animationDelay: "300ms" }}
                        />
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-foreground mb-2">مرحباً بك في IC AI</h2>
              <p className="text-muted-foreground mb-6">ابدأ محادثة جديدة للتحدث مع المساعد الذكي</p>
              <Button onClick={createNewConversation} variant="hero" size="lg" className="gap-2">
                <Plus className="h-5 w-5" />
                ابدأ محادثة جديدة
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Chat;