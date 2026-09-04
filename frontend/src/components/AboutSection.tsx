import { motion } from "framer-motion";

const AboutSection = () => {
  return (
    <section id="about" className="section-padding bg-background">
      <div className="container mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="max-w-4xl mx-auto text-center"
        >
          <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground mb-2">
            About Our <span className="text-accent">Institution</span>
          </h2>
          <div className="w-20 h-1 bg-accent mx-auto mb-8 rounded-full" />
          <p className="text-muted-foreground text-lg leading-relaxed mb-6">
            Our College of Engineering was established with a vision to provide quality education and technical competencies on a strong foundation of values, ideals, and rich culture. We offer programs in engineering, technology, and management that prepare students to act as leaders for the promotion of economic and industrial growth.
          </p>
          <p className="text-muted-foreground text-lg leading-relaxed">
            We integrate classroom learning with industry exposure to ensure the application of knowledge during the course of study itself. Our state-of-the-art infrastructure, experienced faculty, and vibrant campus life create an ideal environment for holistic development.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8 mt-16">
          {[
            { title: "Our Vision", desc: "To be a globally recognized institution of excellence in engineering education, research, and innovation." },
            { title: "Our Mission", desc: "To impart quality education, foster creativity, and develop ethical leaders who contribute to society." },
            { title: "Our Values", desc: "Integrity, innovation, inclusivity, and a commitment to academic excellence and social responsibility." },
          ].map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.15 }}
              className="p-8 bg-card rounded-xl border border-border shadow-sm hover:shadow-lg transition-shadow"
            >
              <h3 className="font-display text-xl font-bold text-foreground mb-3">{item.title}</h3>
              <p className="text-muted-foreground leading-relaxed">{item.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default AboutSection;
