import { useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Eye, EyeOff, Mail, Lock, User, ArrowRight, Building, Briefcase, Phone } from "lucide-react";
import logo from "@/assets/logo.png";
import { toast } from "@/hooks/use-toast";

interface UserData {
  name: string;
  email: string;
  password: string;
  phone?: string;
  countryCode?: string;
  organization?: string;
  jobTitle?: string;
}

const Auth = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(searchParams.get("mode") !== "signup");
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [countryCode, setCountryCode] = useState("+966");
  const [organization, setOrganization] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Get all registered users from localStorage
  const getUsers = (): UserData[] => {
    const usersData = localStorage.getItem("ic_users");
    return usersData ? JSON.parse(usersData) : [];
  };

  // Save users to localStorage
  const saveUsers = (users: UserData[]) => {
    localStorage.setItem("ic_users", JSON.stringify(users));
  };

  // Find user by email
  const findUserByEmail = (email: string): UserData | undefined => {
    const users = getUsers();
    return users.find(user => user.email.toLowerCase() === email.toLowerCase());
  };

  // Validate email format
  const isValidEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // Validate password strength
  const isValidPassword = (password: string): boolean => {
    return password.length >= 6;
  };

  // Validate phone number
  const isValidPhone = (phone: string): boolean => {
    return phone.length >= 9;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate required fields
    if (!email || !password || (!isLogin && !name)) {
      toast({
        title: "خطأ",
        description: "يرجى ملء جميع الحقول المطلوبة",
        variant: "destructive",
      });
      return;
    }

    // Validate email format
    if (!isValidEmail(email)) {
      toast({
        title: "خطأ",
        description: "البريد الإلكتروني غير صحيح",
        variant: "destructive",
      });
      return;
    }

    // Validate password strength
    if (!isValidPassword(password)) {
      toast({
        title: "خطأ",
        description: "كلمة المرور يجب أن تكون 6 أحرف على الأقل",
        variant: "destructive",
      });
      return;
    }

    // Validate phone for signup
    if (!isLogin && phone && !isValidPhone(phone)) {
      toast({
        title: "خطأ",
        description: "رقم الهاتف غير صحيح",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);

    // Simulate async authentication
    setTimeout(() => {
      if (isLogin) {
        // Login Logic
        const existingUser = findUserByEmail(email);
        
        if (!existingUser) {
          toast({
            title: "خطأ في تسجيل الدخول",
            description: "البريد الإلكتروني غير مسجل. يرجى إنشاء حساب جديد.",
            variant: "destructive",
          });
          setIsLoading(false);
          return;
        }

        if (existingUser.password !== password) {
          toast({
            title: "خطأ في تسجيل الدخول",
            description: "كلمة المرور غير صحيحة. يرجى المحاولة مرة أخرى.",
            variant: "destructive",
          });
          setIsLoading(false);
          return;
        }

        // Successful login
        const userData = {
          name: existingUser.name,
          email: existingUser.email,
          phone: existingUser.phone || "",
          countryCode: existingUser.countryCode || "+966",
          organization: existingUser.organization || "",
          jobTitle: existingUser.jobTitle || "",
        };
        
        localStorage.setItem("ic_user", JSON.stringify(userData));
        
        toast({
          title: "تم تسجيل الدخول بنجاح",
          description: `مرحباً ${existingUser.name}!`,
        });

        setTimeout(() => {
          navigate("/chat");
        }, 500);
      } else {
        // Signup Logic
        const existingUser = findUserByEmail(email);
        
        if (existingUser) {
          toast({
            title: "خطأ في إنشاء الحساب",
            description: "البريد الإلكتروني مسجل مسبقاً. يرجى تسجيل الدخول.",
            variant: "destructive",
          });
          setIsLoading(false);
          return;
        }

        // Validate name
        if (name.trim().length < 2) {
          toast({
            title: "خطأ",
            description: "الاسم يجب أن يكون حرفين على الأقل",
            variant: "destructive",
          });
          setIsLoading(false);
          return;
        }

        // Create new user
        const newUser: UserData = {
          name: name.trim(),
          email: email.toLowerCase(),
          password: password,
          phone: phone || "",
          countryCode: countryCode,
          organization: organization.trim() || "",
          jobTitle: jobTitle.trim() || "",
        };

        const users = getUsers();
        users.push(newUser);
        saveUsers(users);

        // Set current user
        const userData = {
          name: newUser.name,
          email: newUser.email,
          phone: newUser.phone,
          countryCode: newUser.countryCode,
          organization: newUser.organization,
          jobTitle: newUser.jobTitle,
        };
        
        localStorage.setItem("ic_user", JSON.stringify(userData));
        
        toast({
          title: "تم إنشاء الحساب بنجاح",
          description: `مرحباً ${newUser.name}! جاري توجيهك إلى صفحة المحادثة...`,
        });

        setTimeout(() => {
          navigate("/chat");
        }, 500);
      }
      
      setIsLoading(false);
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left Side - Form */}
      <div className="flex-1 flex flex-col justify-center items-center px-8 py-12">
        <div className="w-full max-w-md">
          {/* Logo & Back */}
          <div className="mb-8">
            <Link to="/" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
              <ArrowRight className="h-4 w-4" />
              <span>العودة للرئيسية</span>
            </Link>
          </div>

          {/* Header */}
          <div className="text-center mb-8">
            <img src={logo} alt="IC AI" className="h-16 w-auto mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-foreground mb-2">
              {isLogin ? "مرحباً بعودتك!" : "إنشاء حساب جديد"}
            </h1>
            <p className="text-muted-foreground">
              {isLogin
                ? "سجل دخولك للمتابعة"
                : "انضم إلينا واستمتع بتجربة الذكاء الاصطناعي"}
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {!isLogin && (
              <div className="space-y-2">
                <Label htmlFor="name" className="text-foreground">
                  الاسم الكامل <span className="text-destructive">*</span>
                </Label>
                <div className="relative">
                  <User className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                  <Input
                    id="name"
                    type="text"
                    placeholder="أدخل اسمك"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="pr-11 h-12 bg-card border-border focus:border-secondary"
                  />
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="text-foreground">
                البريد الإلكتروني <span className="text-destructive">*</span>
              </Label>
              <div className="relative">
                <Mail className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="example@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pr-11 h-12 bg-card border-border focus:border-secondary"
                  dir="ltr"
                />
              </div>
            </div>

            {!isLogin && (
              <div className="space-y-2">
                <Label htmlFor="phone" className="text-foreground">
                  رقم الهاتف
                </Label>
                <div className="flex gap-2">
                  <select
                    value={countryCode}
                    onChange={(e) => setCountryCode(e.target.value)}
                    className="h-12 w-24 rounded-lg bg-card border border-border px-3 text-sm focus:border-secondary focus:outline-none"
                    dir="ltr"
                  >
                    <option value="+966">🇸🇦 +966</option>
                    <option value="+971">🇦🇪 +971</option>
                    <option value="+965">🇰🇼 +965</option>
                    <option value="+973">🇧🇭 +973</option>
                    <option value="+974">🇶🇦 +974</option>
                    <option value="+968">🇴🇲 +968</option>
                    <option value="+962">🇯🇴 +962</option>
                    <option value="+20">🇪🇬 +20</option>
                  </select>
                  <div className="relative flex-1">
                    <Phone className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                    <Input
                      id="phone"
                      type="tel"
                      placeholder="5xxxxxxxx"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
                      className="pr-11 h-12 bg-card border-border focus:border-secondary"
                      dir="ltr"
                    />
                  </div>
                </div>
              </div>
            )}

            {!isLogin && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="organization" className="text-foreground">
                    اسم الجهة / المؤسسة
                  </Label>
                  <div className="relative">
                    <Building className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                    <Input
                      id="organization"
                      type="text"
                      placeholder="اسم الشركة أو المؤسسة"
                      value={organization}
                      onChange={(e) => setOrganization(e.target.value)}
                      className="pr-11 h-12 bg-card border-border focus:border-secondary"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="jobTitle" className="text-foreground">
                    المسمى الوظيفي
                  </Label>
                  <div className="relative">
                    <Briefcase className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                    <Input
                      id="jobTitle"
                      type="text"
                      placeholder="مثال: مدير، محلل، مهندس..."
                      value={jobTitle}
                      onChange={(e) => setJobTitle(e.target.value)}
                      className="pr-11 h-12 bg-card border-border focus:border-secondary"
                    />
                  </div>
                </div>
              </>
            )}

            <div className="space-y-2">
              <Label htmlFor="password" className="text-foreground">
                كلمة المرور <span className="text-destructive">*</span>
              </Label>
              <div className="relative">
                <Lock className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pr-11 pl-11 h-12 bg-card border-border focus:border-secondary"
                  dir="ltr"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
              {!isLogin && (
                <p className="text-xs text-muted-foreground mt-1">
                  كلمة المرور يجب أن تكون 6 أحرف على الأقل
                </p>
              )}
            </div>

            {isLogin && (
              <div className="flex justify-end">
                <button
                  type="button"
                  className="text-sm text-secondary hover:underline"
                  onClick={() => {
                    toast({
                      title: "استعادة كلمة المرور",
                      description: "يرجى التواصل مع الدعم الفني لاستعادة حسابك",
                    });
                  }}
                >
                  نسيت كلمة المرور؟
                </button>
              </div>
            )}

            <Button 
              type="submit" 
              variant="hero" 
              size="lg" 
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? "جاري التحميل..." : isLogin ? "تسجيل الدخول" : "إنشاء حساب"}
            </Button>
          </form>

          {/* Switch Mode */}
          <div className="mt-8 text-center">
            <p className="text-muted-foreground">
              {isLogin ? "ليس لديك حساب؟" : "لديك حساب بالفعل؟"}{" "}
              <button
                onClick={() => {
                  setIsLogin(!isLogin);
                  // Reset form when switching modes
                  setEmail("");
                  setPassword("");
                  setName("");
                  setPhone("");
                  setOrganization("");
                  setJobTitle("");
                }}
                className="text-secondary font-semibold hover:underline"
              >
                {isLogin ? "إنشاء حساب جديد" : "تسجيل الدخول"}
              </button>
            </p>
          </div>
        </div>
      </div>

      {/* Right Side - Decoration */}
      <div className="hidden lg:flex flex-1 gradient-hero relative overflow-hidden">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center text-primary-foreground p-12">
            <div className="float-animation mb-8">
              <img 
                src={logo} 
                alt="IC AI" 
                className="h-40 w-auto mx-auto glow-effect rounded-3xl p-4 bg-card/10"
              />
            </div>
            <h2 className="text-3xl font-bold mb-4">
              {isLogin ? "أهلاً بك مجدداً" : "مرحباً بك في IC AI"}
            </h2>
            <p className="text-primary-foreground/80 max-w-sm mx-auto">
              استمتع بتجربة فريدة مع مساعدك الذكي الذي يفهم احتياجاتك ويساعدك على تحقيق أهدافك
            </p>
          </div>
        </div>
        
        {/* Decorative circles */}
        <div className="absolute top-10 left-10 w-32 h-32 bg-secondary/20 rounded-full blur-2xl" />
        <div className="absolute bottom-20 right-20 w-48 h-48 bg-accent/20 rounded-full blur-3xl" />
        <div className="absolute top-1/3 right-10 w-24 h-24 bg-blue-lighter/30 rounded-full blur-xl" />
      </div>
    </div>
  );
};

export default Auth;