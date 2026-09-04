import { motion } from "framer-motion";

const stats = [
  { value: "5000+", label: "Students" },
  { value: "200+", label: "Faculty Members" },
  { value: "95%", label: "Placement Rate" },
  { value: "50+", label: "Recruiters" },
  { value: "18+", label: "Years of Excellence" },
  { value: "7", label: "Departments" },
];

const StatsSection = () => {
  return (
    <section id="stats" className="py-20 bg-primary relative overflow-hidden">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-0 left-0 w-64 h-64 rounded-full bg-accent blur-3xl" />
        <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-accent blur-3xl" />
      </div>
      <div className="container mx-auto px-4 relative z-10">
        <div className="text-center mb-12">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-primary-foreground mb-2">
            Our Achievements
          </h2>
          <div className="w-20 h-1 bg-accent mx-auto rounded-full" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-8">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.1 }}
              className="text-center"
            >
              <p className="font-display text-3xl md:text-4xl font-bold text-accent mb-1">{stat.value}</p>
              <p className="text-primary-foreground/70 text-sm font-medium">{stat.label}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default StatsSection;
