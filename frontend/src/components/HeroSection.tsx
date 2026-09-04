import { motion } from "framer-motion";
import heroCampus from "@/assets/college1.jpg";

const HeroSection = () => {
  return (
<section className="relative min-h-screen flex items-center overflow-hidden">
      <img
        src={heroCampus}
        alt="College Campus"
        className="absolute inset-0 w-full h-full object-cover"
      />
      <div className="absolute inset-0 hero-overlay" />
<div className="relative z-10 container mx-auto px-4 flex items-center min-h-screen">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="max-w-3xl"
        >
          <h1 className="font-display text-4xl md:text-6xl font-bold text-primary-foreground leading-tight mb-4">
            Shaping Future
            <span className="block gold-accent">Leaders & Innovators</span>
          </h1>
          <p className="text-primary-foreground/85 text-lg md:text-xl mb-8 font-body max-w-xl">
            Empowering students with quality education, cutting-edge research, and industry-ready skills since 2008.
          </p>
          <div className="flex flex-wrap gap-4">
            <a
              href="#departments"
              className="px-8 py-3 bg-accent text-accent-foreground font-semibold rounded-lg hover:brightness-110 transition-all shadow-lg"
            >
              Explore Programs
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default HeroSection;
