"use client";

import { useEffect, useRef } from "react";

export default function MultilingualSphere() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.min.js";
    script.async = true;

    script.onload = () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const THREE = (window as any).THREE;
      if (!THREE || !container) return;

      const width = container.clientWidth || 700;
      const height = container.clientHeight || 560;

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
      camera.position.set(0, 0, 7.5);

      const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      container.appendChild(renderer.domElement);

      const mainGroup = new THREE.Group();
      scene.add(mainGroup);

      scene.add(new THREE.AmbientLight(0xffffff, 0.85));
      const dirLight1 = new THREE.DirectionalLight(0xff4500, 2.5);
      dirLight1.position.set(5, 5, 4);
      scene.add(dirLight1);
      const dirLight2 = new THREE.DirectionalLight(0x38bdf8, 1.8);
      dirLight2.position.set(-5, -3, 3);
      scene.add(dirLight2);

      const coreMesh = new THREE.Mesh(
        new THREE.IcosahedronGeometry(1.6, 3),
        new THREE.MeshPhongMaterial({
          color: 0x0f172a, emissive: 0x1e293b,
          wireframe: true, transparent: true, opacity: 0.35, shininess: 90,
        })
      );
      mainGroup.add(coreMesh);

      const innerMesh = new THREE.Mesh(
        new THREE.SphereGeometry(1.1, 32, 32),
        new THREE.MeshLambertMaterial({ color: 0xe11d48, transparent: true, opacity: 0.15 })
      );
      mainGroup.add(innerMesh);

      const nodesGroup = new THREE.Group();
      mainGroup.add(nodesGroup);
      const nodeCount = 14;
      const nodeMeshes: { mesh: any; basePos: any; seed: number }[] = [];
      const nodePositions: any[] = [];
      const radius = 2.8;

      for (let i = 0; i < nodeCount; i++) {
        const phi = Math.acos(-1 + (2 * i) / nodeCount);
        const theta = Math.sqrt(nodeCount * Math.PI) * phi;
        const x = radius * Math.cos(theta) * Math.sin(phi);
        const y = radius * Math.sin(theta) * Math.sin(phi) * 0.7;
        const z = radius * Math.cos(phi);
        const nodeSize = i % 3 === 0 ? 0.12 : 0.07;
        const nodeColor = i === 0 ? 0xe11d48 : i % 2 === 0 ? 0xfacc15 : 0x38bdf8;
        const node = new THREE.Mesh(
          new THREE.SphereGeometry(nodeSize, 16, 16),
          new THREE.MeshStandardMaterial({ color: nodeColor, roughness: 0.2, metalness: 0.1 })
        );
        node.position.set(x, y, z);
        nodesGroup.add(node);
        nodeMeshes.push({ mesh: node, basePos: new THREE.Vector3(x, y, z), seed: i * 0.8 });
        nodePositions.push(new THREE.Vector3(x, y, z));
      }

      const lineCoords: number[] = [];
      for (let i = 0; i < nodePositions.length; i++) {
        lineCoords.push(0, 0, 0, nodePositions[i].x, nodePositions[i].y, nodePositions[i].z);
        const next = (i + 1) % nodePositions.length;
        lineCoords.push(nodePositions[i].x, nodePositions[i].y, nodePositions[i].z,
          nodePositions[next].x, nodePositions[next].y, nodePositions[next].z);
      }
      const linesGeo = new THREE.BufferGeometry();
      linesGeo.setAttribute("position", new THREE.Float32BufferAttribute(lineCoords, 3));
      mainGroup.add(new THREE.LineSegments(linesGeo,
        new THREE.LineBasicMaterial({ color: 0x94a3b8, transparent: true, opacity: 0.25 })));

      const ring1 = new THREE.Mesh(
        new THREE.TorusGeometry(3.3, 0.015, 16, 100),
        new THREE.MeshBasicMaterial({ color: 0xe2e8f0, transparent: true, opacity: 0.2 })
      );
      ring1.rotation.x = Math.PI / 2.3;
      mainGroup.add(ring1);

      const ring2 = new THREE.Mesh(
        new THREE.TorusGeometry(3.8, 0.012, 16, 100),
        new THREE.MeshBasicMaterial({ color: 0xfacc15, transparent: true, opacity: 0.25 })
      );
      ring2.rotation.x = -Math.PI / 3;
      ring2.rotation.y = 0.4;
      mainGroup.add(ring2);

      let mouseX = 0, mouseY = 0, targetX = 0, targetY = 0;
      const onMouseMove = (e: MouseEvent) => {
        const rect = container!.getBoundingClientRect();
        mouseX = ((e.clientX - rect.left) / (rect.width || 1)) * 2 - 1;
        mouseY = -(((e.clientY - rect.top) / (rect.height || 1)) * 2 - 1);
      };
      window.addEventListener("mousemove", onMouseMove);

      const onResize = () => {
        const w = container!.clientWidth || window.innerWidth;
        const h = container!.clientHeight || window.innerHeight;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
      };
      window.addEventListener("resize", onResize);

      let frameId: number;
      const clock = new THREE.Clock();
      const animate = () => {
        frameId = requestAnimationFrame(animate);
        const t = clock.getElapsedTime();
        targetX += (mouseX * 0.45 - targetX) * 0.05;
        targetY += (mouseY * 0.35 - targetY) * 0.05;
        mainGroup.rotation.y = t * 0.12 + targetX;
        mainGroup.rotation.x = Math.sin(t * 0.2) * 0.08 - targetY;
        coreMesh.rotation.y = -t * 0.15;
        coreMesh.rotation.z = Math.sin(t * 0.3) * 0.1;
        const s = 1.0 + Math.sin(t * 2.5) * 0.08;
        innerMesh.scale.set(s, s, s);
        for (const item of nodeMeshes) {
          const offset = Math.sin(t * 2.0 + item.seed) * 0.08;
          item.mesh.position.set(
            item.basePos.x * (1 + offset),
            item.basePos.y * (1 + offset),
            item.basePos.z * (1 + offset)
          );
        }
        ring1.rotation.z = t * 0.05;
        ring2.rotation.z = -t * 0.04;
        renderer.render(scene, camera);
      };
      animate();

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (container as any)._threeCleanup = () => {
        cancelAnimationFrame(frameId);
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("resize", onResize);
        renderer.dispose();
        if (container && renderer.domElement.parentNode === container) {
          container.removeChild(renderer.domElement);
        }
      };
    };

    document.head.appendChild(script);

    return () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const el = containerRef.current as any;
      if (el?._threeCleanup) el._threeCleanup();
      if (script.parentNode) script.parentNode.removeChild(script);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
      aria-hidden="true"
    />
  );
}
