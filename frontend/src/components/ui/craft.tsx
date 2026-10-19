import React from "react";
import { cn } from "@/lib/utils";

export interface LayoutProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
}

/**
 * Semantic Section with standard vertical rhythm and padding
 */
export const Section = React.forwardRef<HTMLElement, React.HTMLAttributes<HTMLElement>>(
  ({ children, className, ...props }, ref) => {
    return (
      <section
        ref={ref}
        className={cn("w-full py-12 sm:py-16 lg:py-24 relative overflow-hidden", className)}
        {...props}
      >
        {children}
      </section>
    );
  }
);
Section.displayName = "Section";

/**
 * Centered responsive container with standard horizontal padding
 */
export const Container = React.forwardRef<HTMLDivElement, LayoutProps>(
  ({ children, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8", className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);
Container.displayName = "Container";

/**
 * Responsive 12-column Grid wrapper
 */
export const Grid = React.forwardRef<HTMLDivElement, LayoutProps>(
  ({ children, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center", className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);
Grid.displayName = "Grid";

/**
 * Semantic Article container
 */
export const Article = React.forwardRef<HTMLElement, React.HTMLAttributes<HTMLElement>>(
  ({ children, className, ...props }, ref) => {
    return (
      <article
        ref={ref}
        className={cn("w-full max-w-prose mx-auto space-y-4", className)}
        {...props}
      >
        {children}
      </article>
    );
  }
);
Article.displayName = "Article";
