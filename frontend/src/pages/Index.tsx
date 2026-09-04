import Header from "@/components/Header";
import HeroSection from "@/components/HeroSection";
import QuickLinks from "@/components/QuickLinks";
import AboutSection from "@/components/AboutSection";
import DepartmentsSection from "@/components/DepartmentsSection";
import StatsSection from "@/components/StatsSection";
import Footer from "@/components/Footer";
import ChatbotPopup from "@/components/ChatbotPopup";

const Index = () => {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <HeroSection />
      <QuickLinks />
      <AboutSection />
      <DepartmentsSection />
      <StatsSection />
      <Footer />
      <ChatbotPopup />
    </div>
  );
};

export default Index;
