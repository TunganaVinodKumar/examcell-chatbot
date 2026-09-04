import { motion } from "framer-motion";
import { Cpu, Zap, Cog, Building2,Antenna } from "lucide-react";

const departments = [
  { icon: Cpu, name: "Computer Science & Engineering", seats: 120 },
  { icon: Zap, name: "Electrical & Electronics Engineering", seats: 60 },
  { icon: Antenna, name: "Electronics & Communication Engineering", seats: 120 },
  { icon: Cog, name: "Mechanical Engineering", seats: 60 },
  { icon: Building2, name: "Civil Engineering", seats: 60 },
];

const DepartmentsSection = () => {
  return (
    <section id="departments" className="section-padding bg-muted/50">
      <div className="container mx-auto">
        <div className="text-center mb-12">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground mb-2">
            Our <span className="text-accent">Departments</span>
          </h2>
          <div className="w-20 h-1 bg-accent mx-auto mb-4 rounded-full" />
          <p className="text-muted-foreground max-w-2xl mx-auto">
            We offer a wide range of undergraduate and postgraduate programs across various disciplines.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {departments.map((dept, i) => (
            <motion.div
              key={dept.name}
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.1 }}
              className="group p-6 bg-card rounded-xl border border-border hover:border-accent/50 hover:shadow-xl transition-all duration-300 cursor-pointer"
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                  <dept.icon className="w-6 h-6 text-primary group-hover:text-accent transition-colors" />
                </div>
                <div>
                  <h3 className="font-display text-lg font-semibold text-foreground mb-1">{dept.name}</h3>
                  <p className="text-sm text-muted-foreground">Intake: {dept.seats} seats</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default DepartmentsSection;
