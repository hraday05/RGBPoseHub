import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export default function PointCloudViewer3D({ pointCloudData, boundingBox3D, objectName }) {
  const mountRef = useRef(null);
  const [pointSize, setPointSize] = useState(0.012);
  const [showBox, setShowBox] = useState(true);
  const [showAxes, setShowAxes] = useState(true);
  const [showGrid, setShowGrid] = useState(true);
  const [isRotating, setIsRotating] = useState(true);

  // References to keep Three.js instances
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);
  const pointsMeshRef = useRef(null);
  const boxMeshRef = useRef(null);
  const axesMeshRef = useRef(null);
  const gridMeshRef = useRef(null);
  const animFrameIdRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container || !pointCloudData || !pointCloudData.points) return;

    const width = container.clientWidth || 600;
    const height = 460;

    // 1. Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0e17);
    sceneRef.current = scene;

    // 2. Camera setup
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.05, 50);
    // Position camera looking down-angle at the unprojected points
    camera.position.set(0, -0.2, 0.4);

    // 3. WebGL Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mountRef.current.innerHTML = '';
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.screenSpacePanning = true;
    controls.autoRotate = isRotating;
    controls.autoRotateSpeed = 1.2;
    controlsRef.current = controls;

    // 5. Grid and Axes Helpers
    const grid = new THREE.GridHelper(2.5, 25, 0x06b6d4, 0x1e293b);
    grid.rotation.x = Math.PI / 2;
    grid.position.set(0, 0, 1.2);
    grid.visible = showGrid;
    scene.add(grid);
    gridMeshRef.current = grid;

    const axes = new THREE.AxesHelper(0.25);
    axes.position.set(0, 0, 1.0);
    axes.visible = showAxes;
    scene.add(axes);
    axesMeshRef.current = axes;

    // 6. Build 3D Point Cloud from (X, Y, Z, R, G, B)
    const pointsList = pointCloudData.points;
    const numPoints = pointsList.length;

    const positions = new Float32Array(numPoints * 3);
    const colors = new Float32Array(numPoints * 3);

    let sumX = 0, sumY = 0, sumZ = 0;

    for (let i = 0; i < numPoints; i++) {
      const p = pointsList[i];
      // Invert Y to match Three.js coordinate system (Three.js +Y is up, camera +Y is down)
      const px = p[0];
      const py = -p[1];
      const pz = p[2];

      positions[i * 3 + 0] = px;
      positions[i * 3 + 1] = py;
      positions[i * 3 + 2] = pz;

      colors[i * 3 + 0] = p[3];
      colors[i * 3 + 1] = p[4];
      colors[i * 3 + 2] = p[5];

      sumX += px;
      sumY += py;
      sumZ += pz;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: pointSize,
      vertexColors: true,
      sizeAttenuation: true,
      transparent: false,
    });

    const pointsMesh = new THREE.Points(geometry, material);
    scene.add(pointsMesh);
    pointsMeshRef.current = pointsMesh;

    // Center camera target on point cloud centroid
    if (numPoints > 0) {
      const avgX = sumX / numPoints;
      const avgY = sumY / numPoints;
      const avgZ = sumZ / numPoints;
      controls.target.set(avgX, avgY, avgZ);
      camera.position.set(avgX, avgY - 0.4, avgZ - 0.7);
      controls.update();
    }

    // 7. Render 3D Bounding Box Wireframe if available
    if (boundingBox3D && boundingBox3D.corners_3d_cam) {
      const corners = boundingBox3D.corners_3d_cam; // 8 corners
      // Invert Y for Three.js
      const tCorners = corners.map(c => new THREE.Vector3(c[0], -c[1], c[2]));

      // 12 box edges
      const edgeIndices = [
        [0, 1], [1, 2], [2, 3], [3, 0], // Front face
        [4, 5], [5, 6], [6, 7], [7, 4], // Back face
        [0, 4], [1, 5], [2, 6], [3, 7], // Connecting edges
      ];

      const boxPoints = [];
      edgeIndices.forEach(([i, j]) => {
        boxPoints.push(tCorners[i]);
        boxPoints.push(tCorners[j]);
      });

      const boxGeo = new THREE.BufferGeometry().setFromPoints(boxPoints);
      const boxMat = new THREE.LineBasicMaterial({
        color: 0x10b981,
        linewidth: 3,
        transparent: true,
        opacity: 0.9,
      });

      const boxMesh = new THREE.LineSegments(boxGeo, boxMat);
      boxMesh.visible = showBox;
      scene.add(boxMesh);
      boxMeshRef.current = boxMesh;
    }

    // 8. Animation Loop
    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // 9. Resize handler
    const handleResize = () => {
      if (!mountRef.current) return;
      const newWidth = mountRef.current.clientWidth;
      camera.aspect = newWidth / height;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, height);
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
      if (renderer.domElement && container) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
      geometry.dispose();
      material.dispose();
    };
  }, [pointCloudData, boundingBox3D]);

  // Dynamic property updates without full re-render
  useEffect(() => {
    if (pointsMeshRef.current) {
      pointsMeshRef.current.material.size = pointSize;
      pointsMeshRef.current.material.needsUpdate = true;
    }
  }, [pointSize]);

  useEffect(() => {
    if (boxMeshRef.current) boxMeshRef.current.visible = showBox;
  }, [showBox]);

  useEffect(() => {
    if (axesMeshRef.current) axesMeshRef.current.visible = showAxes;
  }, [showAxes]);

  useEffect(() => {
    if (gridMeshRef.current) gridMeshRef.current.visible = showGrid;
  }, [showGrid]);

  useEffect(() => {
    if (controlsRef.current) controlsRef.current.autoRotate = isRotating;
  }, [isRotating]);

  const handleResetCamera = () => {
    if (!controlsRef.current || !pointCloudData?.points) return;
    const pts = pointCloudData.points;
    if (pts.length === 0) return;
    const avgX = pts[0][0];
    const avgY = -pts[0][1];
    const avgZ = pts[0][2];
    controlsRef.current.target.set(avgX, avgY, avgZ);
    controlsRef.current.object.position.set(avgX, avgY - 0.4, avgZ - 0.7);
    controlsRef.current.update();
  };

  return (
    <div style={{
      background: 'linear-gradient(145deg, #0d1322, #070a12)',
      border: '1px solid rgba(56, 189, 248, 0.25)',
      borderRadius: '16px',
      overflow: 'hidden',
      boxShadow: '0 20px 40px -15px rgba(0,0,0,0.7), 0 0 25px -5px rgba(6, 182, 212, 0.15)',
      marginTop: '1.5rem',
      position: 'relative',
    }}>
      {/* 3D Canvas Header & Controls Bar */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '1rem 1.25rem',
        background: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        gap: '1rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(6, 182, 212, 0.4)',
            fontSize: '1.2rem',
          }}>
            🪐
          </div>
          <div>
            <h4 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600, color: '#f8fafc', letterSpacing: '-0.01em' }}>
              Interactive 3D Spatial Point Cloud
            </h4>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
              Real-time WebGL depth unprojection &bull; {pointCloudData?.total_points?.toLocaleString() || 0} reconstructed points
            </span>
          </div>
        </div>

        {/* Quick Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setIsRotating(!isRotating)}
            style={{
              background: isRotating ? 'rgba(6, 182, 212, 0.2)' : 'rgba(255, 255, 255, 0.06)',
              border: `1px solid ${isRotating ? '#06b6d4' : 'rgba(255, 255, 255, 0.15)'}`,
              color: isRotating ? '#38bdf8' : '#cbd5e1',
              padding: '0.4rem 0.8rem',
              borderRadius: '8px',
              fontSize: '0.8rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              transition: 'all 0.2s',
            }}
          >
            {isRotating ? '⏸ Pause Orbit' : '▶️ Auto Rotate'}
          </button>

          <button
            onClick={() => setShowBox(!showBox)}
            style={{
              background: showBox ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.06)',
              border: `1px solid ${showBox ? '#10b981' : 'rgba(255, 255, 255, 0.15)'}`,
              color: showBox ? '#34d399' : '#cbd5e1',
              padding: '0.4rem 0.8rem',
              borderRadius: '8px',
              fontSize: '0.8rem',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            📦 {showBox ? 'Hide 3D Box' : 'Show 3D Box'}
          </button>

          <button
            onClick={() => setShowAxes(!showAxes)}
            style={{
              background: showAxes ? 'rgba(245, 158, 11, 0.2)' : 'rgba(255, 255, 255, 0.06)',
              border: `1px solid ${showAxes ? '#f59e0b' : 'rgba(255, 255, 255, 0.15)'}`,
              color: showAxes ? '#fbbf24' : '#cbd5e1',
              padding: '0.4rem 0.8rem',
              borderRadius: '8px',
              fontSize: '0.8rem',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            🎯 XYZ Axes
          </button>

          <button
            onClick={handleResetCamera}
            style={{
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: '#f1f5f9',
              padding: '0.4rem 0.8rem',
              borderRadius: '8px',
              fontSize: '0.8rem',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            🔄 Reset View
          </button>
        </div>
      </div>

      {/* Point Size Adjuster Toolbar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.5rem 1.25rem',
        background: 'rgba(15, 23, 42, 0.5)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
        fontSize: '0.8rem',
        color: '#94a3b8',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span>Voxel Size:</span>
          <input
            type="range"
            min="0.004"
            max="0.035"
            step="0.002"
            value={pointSize}
            onChange={(e) => setPointSize(parseFloat(e.target.value))}
            style={{
              cursor: 'pointer',
              accentColor: '#06b6d4',
              width: '120px',
            }}
          />
          <span style={{ fontFamily: 'var(--mono)', color: '#38bdf8' }}>{pointSize.toFixed(3)}m</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span>🖱️ <strong>Left Click + Drag:</strong> 360° Orbit</span>
          <span>📜 <strong>Scroll:</strong> Zoom</span>
          <span>🖱️ <strong>Right Click:</strong> Pan</span>
        </div>
      </div>

      {/* WebGL Canvas Container */}
      <div
        ref={mountRef}
        style={{
          width: '100%',
          height: '460px',
          cursor: 'grab',
          position: 'relative',
        }}
      />

      {/* Floating HUD metrics */}
      {pointCloudData?.bounds && (
        <div style={{
          position: 'absolute',
          bottom: '12px',
          left: '12px',
          background: 'rgba(10, 14, 23, 0.8)',
          backdropFilter: 'blur(8px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '8px',
          padding: '0.5rem 0.85rem',
          fontSize: '0.75rem',
          color: '#cbd5e1',
          fontFamily: 'var(--mono)',
          display: 'flex',
          gap: '1.25rem',
          pointerEvents: 'none',
        }}>
          <div><strong>X:</strong> [{pointCloudData.bounds.min_x.toFixed(2)}, {pointCloudData.bounds.max_x.toFixed(2)}]m</div>
          <div><strong>Y:</strong> [{pointCloudData.bounds.min_y.toFixed(2)}, {pointCloudData.bounds.max_y.toFixed(2)}]m</div>
          <div><strong>Z (Depth):</strong> [{pointCloudData.bounds.min_z.toFixed(2)}, {pointCloudData.bounds.max_z.toFixed(2)}]m</div>
        </div>
      )}
    </div>
  );
}
