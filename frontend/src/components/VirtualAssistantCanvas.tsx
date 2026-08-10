import { useEffect, useRef } from "react";
import * as THREE from "three";

interface VirtualAssistantCanvasProps {
  animationState: "idle" | "talking" | "scanning" | "success" | "denied";
}

export default function VirtualAssistantCanvas({ animationState }: VirtualAssistantCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef(animationState);

  // Sync animationState with a ref to avoid stale closure in the Three.js animation loop
  useEffect(() => {
    stateRef.current = animationState;
  }, [animationState]);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // 1. Scene setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x020617, 0.15);

    // 2. Camera setup
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100);
    camera.position.z = 5;

    // 3. Renderer setup with anti-aliasing
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // 4. Create Holographic Core (Wireframe Sphere)
    const coreGeometry = new THREE.SphereGeometry(1.2, 32, 32);
    const coreMaterial = new THREE.MeshBasicMaterial({
      color: 0x06b6d4, // Cyan by default
      wireframe: true,
      transparent: true,
      opacity: 0.8,
    });
    const core = new THREE.Mesh(coreGeometry, coreMaterial);
    scene.add(core);

    // 5. Create inner glowing core
    const innerGeometry = new THREE.IcosahedronGeometry(0.7, 2);
    const innerMaterial = new THREE.MeshBasicMaterial({
      color: 0x0891b2,
      wireframe: true,
      transparent: true,
      opacity: 0.4,
    });
    const innerCore = new THREE.Mesh(innerGeometry, innerMaterial);
    scene.add(innerCore);

    // 6. Create Orbiting Particle Rings
    const particleCount = 200;
    const particlesGeometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    // Generate particles in rings around the core
    for (let i = 0; i < particleCount; i++) {
      const angle = (i / particleCount) * Math.PI * 2;
      const radius = 1.6 + Math.random() * 0.6;
      // Some variance in height to make a thick disk
      const y = (Math.random() - 0.5) * 0.4;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      // Cyan-blue gradient colors
      colors[i * 3] = 0.0; // R
      colors[i * 3 + 1] = 0.7 + Math.random() * 0.3; // G
      colors[i * 3 + 2] = 0.9; // B
    }

    particlesGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    particlesGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    // Custom glowing particle material
    // Creating a small canvas-based texture for round, glowing particles
    const pCanvas = document.createElement("canvas");
    pCanvas.width = 16;
    pCanvas.height = 16;
    const pCtx = pCanvas.getContext("2d");
    if (pCtx) {
      const grad = pCtx.createRadialGradient(8, 8, 0, 8, 8, 8);
      grad.addColorStop(0, "rgba(255, 255, 255, 1)");
      grad.addColorStop(0.3, "rgba(103, 232, 249, 0.8)");
      grad.addColorStop(1, "rgba(0, 0, 0, 0)");
      pCtx.fillStyle = grad;
      pCtx.fillRect(0, 0, 16, 16);
    }
    const particleTexture = new THREE.CanvasTexture(pCanvas);

    const particlesMaterial = new THREE.PointsMaterial({
      size: 0.18,
      map: particleTexture,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      vertexColors: true,
    });

    const particleSystem = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particleSystem);

    // 7. Scanning Laser Plane (useful for "scanning" state)
    const laserGeometry = new THREE.RingGeometry(0.1, 2.0, 32);
    const laserMaterial = new THREE.MeshBasicMaterial({
      color: 0x22d3ee,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.0, // Hidden by default
      wireframe: true,
    });
    const laserPlane = new THREE.Mesh(laserGeometry, laserMaterial);
    laserPlane.rotation.x = Math.PI / 2;
    scene.add(laserPlane);

    // 8. Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    // 9. Animation variables
    let clock = new THREE.Clock();
    let animationFrameId: number;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      const elapsedTime = clock.getElapsedTime();
      const current = stateRef.current;

      // Base rotations
      core.rotation.y = elapsedTime * 0.2;
      core.rotation.x = elapsedTime * 0.1;
      innerCore.rotation.y = -elapsedTime * 0.4;
      innerCore.rotation.z = elapsedTime * 0.2;
      particleSystem.rotation.y = elapsedTime * 0.15;

      // Reset laser visibility unless scanning
      laserPlane.visible = current === "scanning";

      // Reactive state behaviors
      if (current === "talking") {
        // High-tech talking wave: pulse scale based on sine wave
        const pulse = 1.0 + Math.sin(elapsedTime * 12) * 0.18;
        core.scale.set(pulse, pulse, pulse);
        innerCore.scale.set(pulse * 0.9, pulse * 0.9, pulse * 0.9);

        // Warm up particles & rotation
        particleSystem.rotation.y = elapsedTime * 0.8;
        coreMaterial.color.setHex(0x06b6d4); // Cyan
        innerMaterial.color.setHex(0x22d3ee);
        coreMaterial.opacity = 0.9;
      } else if (current === "scanning") {
        // Scanning laser animation up and down
        const laserY = Math.sin(elapsedTime * 4) * 1.5;
        laserPlane.position.y = laserY;
        laserMaterial.opacity = 0.5 + Math.sin(elapsedTime * 10) * 0.2;

        // Fast particles, core stays steady
        const pulse = 1.0 + Math.sin(elapsedTime * 2) * 0.03;
        core.scale.set(pulse, pulse, pulse);
        coreMaterial.color.setHex(0x3b82f6); // Royal Blue
        innerMaterial.color.setHex(0x60a5fa);
        laserMaterial.color.setHex(0x3b82f6);
        particleSystem.rotation.y = elapsedTime * 1.5;
      } else if (current === "success") {
        // Success: Emerald Green, celebrating spin
        const pulse = 1.1 + Math.sin(elapsedTime * 8) * 0.05;
        core.scale.set(pulse, pulse, pulse);
        coreMaterial.color.setHex(0x10b981); // Emerald Green
        innerMaterial.color.setHex(0x34d399);
        coreMaterial.opacity = 0.95;
        particleSystem.rotation.y = elapsedTime * 2.0;

        // Slowly expand orbits
        const scaleVal = 1.0 + Math.sin(elapsedTime * 2) * 0.1;
        particleSystem.scale.set(scaleVal, 1, scaleVal);
      } else if (current === "denied") {
        // Denied/Error: Crimson Red, jagged shaking pulse
        const shake = Math.sin(elapsedTime * 30) * 0.05;
        const pulse = 0.9 + Math.sin(elapsedTime * 20) * 0.12;
        core.scale.set(pulse, pulse, pulse);
        core.position.set(shake, shake, 0);
        innerCore.position.set(-shake, 0, shake);

        coreMaterial.color.setHex(0xef4444); // Crimson Red
        innerMaterial.color.setHex(0xf87171);
        coreMaterial.opacity = 0.95;
        particleSystem.rotation.y = elapsedTime * -1.2;
      } else {
        // Idle: Soft slow blue/cyan breath
        const pulse = 1.0 + Math.sin(elapsedTime * 2.0) * 0.05;
        core.scale.set(pulse, pulse, pulse);
        core.position.set(0, 0, 0);
        innerCore.position.set(0, 0, 0);
        innerCore.scale.set(0.7, 0.7, 0.7);

        coreMaterial.color.setHex(0x0891b2); // Cyan 600
        innerMaterial.color.setHex(0x0e7490);
        coreMaterial.opacity = 0.6;
        particleSystem.rotation.y = elapsedTime * 0.25;
        particleSystem.scale.set(1, 1, 1);
      }

      renderer.render(scene, camera);
    };

    animate();

    // Handle container resizing
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: newWidth, height: newHeight } = entry.contentRect;
        camera.aspect = newWidth / newHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(newWidth, newHeight);
      }
    });
    resizeObserver.observe(container);

    // Cleanup
    return () => {
      resizeObserver.disconnect();
      cancelAnimationFrame(animationFrameId);
      container.removeChild(renderer.domElement);
      coreGeometry.dispose();
      coreMaterial.dispose();
      innerGeometry.dispose();
      innerMaterial.dispose();
      particlesGeometry.dispose();
      particlesMaterial.dispose();
      particleTexture.dispose();
      laserGeometry.dispose();
      laserMaterial.dispose();
      renderer.dispose();
    };
  }, []);

  return (
    <div
      id="three-canvas-container"
      ref={containerRef}
      className="w-full h-full min-h-[180px] sm:min-h-[220px] relative overflow-hidden flex items-center justify-center rounded-lg bg-slate-950/40 border border-cyan-500/10"
    />
  );
}
