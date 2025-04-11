
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
import numpy as np
from matplotlib.animation import FuncAnimation

L1 ='#ffffff'
L2 = '#fafbfc'
B1 =  '#E3E8EC'
D1 = '#1F2328'
H1 = '#1F883D'
NAVBAR_CLR = '#F6F8FA'
NH = '#EAEDF1'

def meter_fig(parent, percentage_value, facecolor=L2, highlight=None, lbl="Spam Rate", lbl_clr=D1, circle_radius=1.5, arc_thickness=0.5, animation_speed=0.25, frame_delay=20):

    if highlight == None:
        highlight = H1 if percentage_value < 10 else "green" if percentage_value < 20 else "orange"


    fig = Figure(figsize=(3, 3), facecolor=facecolor)
    ax = fig.add_subplot(111)
    ax.set_aspect('equal')
    ax.axis("off")

    circle = patches.Circle((0, 0.4), circle_radius, transform=ax.transData._b, color="gray", fill=False, linewidth=2)
    ax.add_patch(circle)

    # Initialize elements for animation
    ax.text(0, -circle_radius+0.2, lbl, color=lbl_clr, fontsize=16, ha="center",  va="top", )
    arc, = ax.plot([], [], lw=arc_thickness * 10, color=highlight)
    knob, = ax.plot([], [], 'o', color=highlight, markersize=arc_thickness * 20)
    percentage_text = ax.text(0, 0.4, "", color=highlight, fontsize=20, ha="center", va="center")

    def calculate_knob_position(angle_deg, radius):
        """Calculate the (x, y) position of a knob on the circumference given an angle in degrees."""
        angle_rad = np.radians(angle_deg)
        x = radius * np.cos(angle_rad)
        y = radius * np.sin(angle_rad)+0.4
        return [x], [y]  # Return lists to satisfy `set_data`

    def update(frame):
        """Update the arc, knob, and percentage text for each frame."""
        current_percentage = frame
        angle_extent = 360 * (current_percentage / 100)  # Map percentage to degrees

        # Generate arc points
        angles = np.linspace(90, 90 - angle_extent, 100)  # Arc starts at 90 degrees
        x_arc = circle_radius * np.cos(np.radians(angles))
        y_arc = circle_radius * np.sin(np.radians(angles)) +0.4

        # Update arc
        arc.set_data(x_arc, y_arc)

        # Update knob position
        knob_x, knob_y = calculate_knob_position(90 - angle_extent, circle_radius)
        knob.set_data(knob_x, knob_y)  # Ensure sequences are passed

        # Update percentage text
        percentage_text.set_text(f"{current_percentage:.1f}%")  # Show decimal for smoother animation

        canvas.draw_idle()  # Ensure updates are reflected on the canvas

        return arc, knob, percentage_text

    # Embed the matplotlib figure in the tkinter parent
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    # canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Animation control
    frames = np.arange(0, percentage_value + animation_speed, animation_speed)  # Finer steps for smoother animation

    def start_animation(index=0):
        if index < len(frames):
            update(frames[index])
            parent.after(frame_delay, start_animation, index + 1)  # Delay for slower animation

    parent.after(100, start_animation)  # Start animation after a short delay

    return canvas

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Percentage Animation")

    # Frame for the animated circle
    frame = tk.Frame(root)
    frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Create and display the animated percentage figure
    canvas = meter_fig(frame, percentage_value=100)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    root.mainloop()