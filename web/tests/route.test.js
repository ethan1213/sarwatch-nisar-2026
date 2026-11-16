import test from 'node:test'
import assert from 'node:assert/strict'
import {validateSegments,routeKm,sampleRoute,terrainAt} from '../src/lib/route.js'
test('GPX segments do not gain invented connecting distance',()=>{
 const a=[[-73,-37],[-73,-36.99]],b=[[-71,-34],[-71,-33.99]]
 assert.ok(Math.abs(routeKm([a,b])-2.2239)<.001)
})
test('invalid coordinates are not accepted as meaningful locations',()=>{
 for(const invalid of [NaN,Infinity,-200,0]) assert.throws(()=>validateSegments([[[-73,-37],[invalid,-37]]]))
 assert.throws(()=>validateSegments([]))
 assert.throws(()=>validateSegments([Array.from({length:20001},()=>[-73,-37])]))
})
test('route sampling bounds cost and retains endpoints',()=>{
 const segment=Array.from({length:100},(_,i)=>[-73+i/1000,-37])
 const points=sampleRoute([segment])
 assert.equal(points.length,20)
 assert.deepEqual(points[0].coordinate,segment[0])
 assert.deepEqual(points.at(-1).coordinate,segment.at(-1))
})
test('outside coverage and polygon holes do not borrow nearby terrain',()=>{
 const feature={geometry:{type:'Polygon',coordinates:[[[0,0],[4,0],[4,4],[0,4],[0,0]],[[1,1],[2,1],[2,2],[1,2],[1,1]]]},properties:{slope_deg:15}}
 assert.equal(terrainAt([3,3],[feature]).slope_deg,15)
 assert.equal(terrainAt([1.5,1.5],[feature]),null)
 assert.equal(terrainAt([5,5],[feature]),null)
})
