import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 8))

# Plot polygons
for poly in getattr(roi, "geoms", [roi]):
    x, y = poly.exterior.xy
    ax.fill(x, y, alpha=0.3, edgecolor="black", facecolor="lightblue")

# roi.plot(ax=ax, facecolor="lightblue", edgecolor="black", alpha=0.3)

# Plot weather points
ax.scatter(
    test_df["lon"],
    test_df["lat"],
    s=8,
    color="red",
    label="Weather points",
)

# Plot start
ax.scatter(
    start[1], start[0],
    color="green",
    s=80,
    marker="o",
    label="Start",
)
ax.text(
    start[1], start[0],
    f"Start\n({start[0]:.4f}, {start[1]:.4f})",
    color="green",
)

# Plot goal
ax.scatter(
    goal[1], goal[0],
    color="blue",
    s=80,
    marker="x",
    label="Goal",
)
ax.text(
    goal[1], goal[0],
    f"Goal\n({goal[0]:.4f}, {goal[1]:.4f})",
    color="blue",
)

ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
ax.legend()

plt.show()