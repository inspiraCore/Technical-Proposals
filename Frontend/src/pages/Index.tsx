import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Sparkles, FileText, Zap, Clock  } from "lucide-react";
import logo from "@/assets/logo.png";
import { useEffect, useState } from "react";

const Index = () => {
  const navigate = useNavigate();
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    // Check if user is logged in
    const user = localStorage.getItem("ic_user");
    setIsLoggedIn(!!user);
  }, []);

  const handleStartChat = () => {
    const user = localStorage.getItem("ic_user");
    if (user) {
      navigate("/chat");
    } else {
      navigate("/auth?mode=signup");
    }
  };

  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* Header */}
      <header className="fixed top-0 right-0 left-0 z-50 bg-background/80 backdrop-blur-lg border-b border-border">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src={logo} alt="InspiraCore AI Logo" className="h-10 w-auto" />
            <span className="text-xl font-bold text-foreground">InspiraCore AI</span>
          </div>
          <div className="flex items-center gap-4">
            <Button 
              variant="secondary" 
              size="sm"
              onClick={handleStartChat}
            >
              {isLoggedIn ? "افتح المحادثة" : "جرب الآن"}
            </Button>
            <Link to="/auth">
              <Button variant="ghost" size="sm">
                تسجيل الدخول
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6">
        {/* Background decorations */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-20 left-10 w-72 h-72 bg-secondary/20 rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-blue-lighter/40 rounded-full blur-3xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent/10 rounded-full blur-3xl" />

          
          {/* Stars - في الزوايا */}
          <Sparkles className="absolute top-20 right-20 h-8 w-8 text-yellow-400 opacity-40 animate-pulse" />
          <Sparkles className="absolute top-20 left-20 h-6 w-6 text-yellow-300 opacity-30" />
          <Sparkles className="absolute bottom-20 right-20 h-7 w-7 text-yellow-400 opacity-35 animate-pulse" style={{ animationDelay: '1.5s' }} />
          <Sparkles className="absolute bottom-20 left-20 h-6 w-6 text-yellow-300 opacity-35" />
        </div>

        <div className="container mx-auto relative z-10">
          <div className="max-w-4xl mx-auto text-center">
            {/* Floating Logo */}
            <div className="float-animation mb-8 inline-block">
              <div className="relative">
                <img 
                  src={logo} 
                  alt="InspiraCore AI" 
                  className="h-32 w-auto mx-auto glow-effect rounded-2xl p-2 bg-card/50"
                />
                <Sparkles className="absolute -top-4 -right-4 h-8 w-8 text-accent animate-pulse" />
              </div>
            </div>

            <h1 className="text-3xl md:text-5xl font-extrabold text-foreground mb-6 leading-tight">
               TechProposal
              <span className="block mt-2 text-secondary font-bold">
                
              </span>
            </h1>

            <p className="text-lg md:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto leading-relaxed">
             أداة ذكية متخصصة في توليد وصياغة العروض الفنية للمنافسات والمشاريع،
تعتمد على تحليل نطاق العمل وكراسة الشروط لإنتاج محتوى فني منظم ومتوافق مع المتطلبات.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button 
                variant="hero" 
                size="xl" 
                className="gap-3"
                onClick={handleStartChat}
              >
                <Sparkles className="h-5 w-5 text-[#E29C3D]" />
                {isLoggedIn ? "افتح المحادثة الآن" : "ابدأ المحادثة الآن"}
              </Button>
              <Link to="/auth">
                <Button variant="outline" size="xl">
                  تسجيل الدخول
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-6">
        <div className="container mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-center text-foreground mb-4">
            لماذا تختار <span className="text-secondary">InspiraCore AI</span>؟
          </h2>
          <p className="text-center text-muted-foreground mb-12 max-w-xl mx-auto">
           الحل الذكي لإعداد العروض الفنية
          </p>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <FeatureCard
              icon={<FileText className="h-8 w-8" />}
              title=" فهم دقيق لكراسة الشروط"
              description="تحليل ذكي لنطاق العمل والمتطلبات الفنية، لاستخلاص النقاط الجوهرية وبناء عرض فني متوافق مع أهداف المشروع."
            />
            <FeatureCard
              icon={<Zap className="h-8 w-8" />}
              title="توليد عروض فنية منهجية "
              description="إنتاج محتوى فني منظم يشمل المنهجية، خطة التنفيذ، والجدول الزمني، بصياغة احترافية قابلة للتعديل والتخصيص"
            />
            <FeatureCard
              icon={<Clock  className="h-8 w-8" />}
              title="توفير الوقت وتقليل الجهد"
              description="تقليل زمن إعداد العروض الفنية بشكل كبير، مع الحفاظ على جودة الصياغة ودقة المحتوى، دون الحاجة للبدء من الصفر."
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6">
        <div className="container mx-auto">
          <div className="gradient-hero rounded-3xl p-12 text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-transparent via-secondary/20 to-accent/20" />
            <div className="relative z-10">
              <h2 className="text-3xl md:text-4xl font-bold text-primary-foreground mb-4">
                جاهز للبدء؟
              </h2>
              <p className="text-primary-foreground/80 mb-8 max-w-lg mx-auto">
                انضم إلى آلاف المستخدمين الذين يستفيدون من قوة الذكاء الاصطناعي يومياً
              </p>
              <Link to="/auth?mode=signup">
                <Button variant="gold" size="xl" className="gap-3">
                  <Sparkles className="h-5 w-5" />
                  إنشاء حساب مجاني
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border">
        <div className="container mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <img src={logo} alt="InspiraCore AI" className="h-8 w-auto" />
            <span className="font-semibold text-foreground">InspiraCore AI</span>
          </div>
          <p className="text-sm text-muted-foreground">
            © 2024 InspiraCore AI. جميع الحقوق محفوظة.
          </p>
        </div>
      </footer>
    </div>
  );
};

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

const FeatureCard = ({ icon, title, description }: FeatureCardProps) => {
  return (
    <div className="gradient-card rounded-2xl p-8 border border-border hover:border-secondary/50 transition-all duration-300 hover:shadow-xl hover:-translate-y-1 group">
      <div className="w-14 h-14 rounded-xl bg-secondary/10 flex items-center justify-center text-secondary mb-5 group-hover:bg-secondary group-hover:text-secondary-foreground transition-all duration-300">
        {icon}
      </div>
      <h3 className="text-xl font-bold text-foreground mb-3">{title}</h3>
      <p className="text-muted-foreground leading-relaxed">{description}</p>
    </div>
  );
};

export default Index;