/*
 Navicat Premium Data Transfer

 Source Server         : PostgreSQL @ tesla
 Source Server Type    : PostgreSQL
 Source Server Version : 90004
 Source Host           : localhost
 Source Database       : googleoffers
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 90004
 File Encoding         : utf-8

 Date: 01/23/2012 14:48:54 PM
*/

-- ----------------------------
--  Table structure for "promotions"
-- ----------------------------
DROP TABLE IF EXISTS "promotions";
CREATE TABLE "promotions" (
	"promotion_id" varchar(100),
	"status" varchar(100),
	"last_update" timestamp(6) NULL
)
WITH (OIDS=FALSE);
ALTER TABLE "promotions" OWNER TO "postgres";


-- ----------------------------
--  Table structure for "redemption_codes"
-- ----------------------------
DROP TABLE IF EXISTS "redemption_codes";
CREATE TABLE "redemption_codes" (
	"size" int4,
	"status" varchar(20),
	"last_update" timestamp(6) NULL,
	"promotion_id" varchar(100)
)
WITH (OIDS=FALSE);
ALTER TABLE "redemption_codes" OWNER TO "postgres";